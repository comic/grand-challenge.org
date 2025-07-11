from datetime import timedelta

import pytest
from dateutil.utils import today
from django.core import mail
from django.utils.timezone import now
from guardian.shortcuts import assign_perm

from grandchallenge.challenges.forms import HTMX_BLANK_CHOICE_KEY
from grandchallenge.challenges.models import (
    Challenge,
    ChallengeRequest,
    OnboardingTask,
)
from grandchallenge.invoices.models import PaymentTypeChoices
from grandchallenge.verifications.models import Verification
from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import (
    ChallengeFactory,
    ChallengeRequestFactory,
    OnboardingTaskFactory,
    UserFactory,
)
from tests.invoices_tests.factories import InvoiceFactory
from tests.utils import get_view_for_user
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
def test_challenge_list(client):
    c = ChallengeFactory(hidden=False)
    hidden = ChallengeFactory(hidden=True)

    response = get_view_for_user(client=client, viewname="challenges:list")

    assert c.short_name in response.rendered_content
    assert hidden.short_name not in response.rendered_content


@pytest.mark.django_db
@pytest.mark.parametrize(
    "phase1_submissions_limit_per_user_per_period,phase1_submissions_open,phase1_submissions_close,phase2_submissions_limit_per_user_per_period,phase2_submissions_open,phase2_submissions_close,expected_status,phase_in_status",
    [
        # both phases are closed (because submission limit 0)
        (
            0,
            None,
            None,
            0,
            None,
            None,
            '<i class="far fa-clock fa-fw"></i> Not accepting submissions',
            None,
        ),
        # both phases closed and completed
        (
            10,
            None,
            now() - timedelta(days=5),
            10,
            None,
            now() - timedelta(days=6),
            '<i class="far fa-clock fa-fw"></i> Challenge completed',
            None,
        ),
        # both phases closed, starting some time in the future
        (
            10,
            now() + timedelta(days=5),
            None,
            10,
            now() + timedelta(days=3),
            None,
            '<i class="far fa-clock fa-fw"></i> Opening submissions',
            1,
        ),
        (
            10,
            now() + timedelta(days=3),
            None,
            10,
            now() + timedelta(days=5),
            None,
            '<i class="far fa-clock fa-fw"></i> Opening submissions',
            0,
        ),
        (
            10,
            now() + timedelta(days=5),
            None,
            10,
            now() + timedelta(days=5),
            None,
            '<i class="far fa-clock fa-fw"></i> Opening submissions',
            0,
        ),
        # both phases closed, one completed, one not started yet
        (
            10,
            now() + timedelta(days=5),
            None,
            10,
            None,
            now() - timedelta(days=6),
            '<i class="far fa-clock fa-fw"></i> Opening submissions',
            0,
        ),
        (
            10,
            None,
            now() - timedelta(days=5),
            10,
            now() + timedelta(days=6),
            None,
            '<i class="far fa-clock fa-fw"></i> Opening submissions',
            1,
        ),
        # phase 1 open, phase 2 closed
        (
            10,
            None,
            None,
            0,
            None,
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            0,
        ),
        (
            10,
            now() - timedelta(days=1),
            None,
            0,
            None,
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            0,
        ),
        (
            10,
            now() - timedelta(days=1),
            now() + timedelta(days=1),
            0,
            None,
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            0,
        ),
        (
            10,
            None,
            now() + timedelta(days=1),
            0,
            None,
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            0,
        ),
        (
            10,
            None,
            None,
            10,
            now() - timedelta(days=10),
            now() - timedelta(days=1),
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            0,
        ),
        (
            10,
            None,
            None,
            10,
            None,
            now() - timedelta(days=1),
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            0,
        ),
        (
            10,
            None,
            None,
            10,
            now() + timedelta(days=10),
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            0,
        ),
        # phase 1 closed, phase 2 open
        (
            0,
            None,
            None,
            10,
            None,
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            1,
        ),
        (
            0,
            None,
            None,
            10,
            now() - timedelta(days=1),
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            1,
        ),
        (
            0,
            None,
            None,
            10,
            now() - timedelta(days=1),
            now() + timedelta(days=1),
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            1,
        ),
        (
            0,
            None,
            None,
            10,
            None,
            now() + timedelta(days=1),
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            1,
        ),
        (
            0,
            None,
            None,
            10,
            now() - timedelta(days=1),
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            1,
        ),
        (
            0,
            None,
            None,
            10,
            now() - timedelta(days=1),
            now() + timedelta(days=1),
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            1,
        ),
        (
            0,
            None,
            None,
            10,
            None,
            now() + timedelta(days=1),
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            1,
        ),
        # both phases open
        (
            10,
            None,
            None,
            10,
            None,
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            None,
        ),
    ],
)
def test_challenge_card_status(
    client,
    phase1_submissions_limit_per_user_per_period,
    phase1_submissions_open,
    phase1_submissions_close,
    phase2_submissions_limit_per_user_per_period,
    phase2_submissions_open,
    phase2_submissions_close,
    expected_status,
    phase_in_status,
):
    ch = ChallengeFactory(hidden=False)
    phase1 = PhaseFactory(challenge=ch)
    phase2 = PhaseFactory(challenge=ch)
    u = UserFactory()

    InvoiceFactory(
        challenge=ch,
        compute_costs_euros=10,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )

    phase1.submissions_limit_per_user_per_period = (
        phase1_submissions_limit_per_user_per_period
    )
    phase1.submissions_open_at = phase1_submissions_open
    phase1.submissions_close_at = phase1_submissions_close
    phase2.submissions_limit_per_user_per_period = (
        phase2_submissions_limit_per_user_per_period
    )
    phase2.submissions_open_at = phase2_submissions_open
    phase2.submissions_close_at = phase2_submissions_close
    phase1.save()
    phase2.save()

    response = get_view_for_user(
        client=client, viewname="challenges:list", user=u
    )
    if phase_in_status:
        title = ch.phase_set.order_by("created").all()[phase_in_status].title
        assert f"{expected_status} for {title}" in response.rendered_content
    else:
        assert expected_status in response.rendered_content


@pytest.mark.django_db
def test_challenge_request_workflow(
    client,
    challenge_reviewer,
):
    challenge_request = ChallengeRequestFactory()
    # requesting a challenge sends email to requester and reviewer(s)
    requester1 = challenge_request.creator
    assert len(mail.outbox) == 2
    receivers = [address for i in mail.outbox for address in i.to]
    assert requester1.email in receivers
    assert challenge_reviewer.email in receivers

    # rejecting a request send email to requester
    mail.outbox.clear()
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-status-update",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_reviewer,
        data={
            "status": ChallengeRequest.ChallengeRequestStatusChoices.REJECTED
        },
    )
    assert response.status_code == 200
    assert len(mail.outbox) == 1
    # rejection email to requester
    assert mail.outbox[0].to == [requester1.email]
    assert (
        "We are very sorry to have to inform you that we will not be able to host your challenge on our platform"
        in mail.outbox[0].body
    )

    # accepting a request sends an email to the requester and creates the challenge
    mail.outbox.clear()
    challenge_request.status = (
        ChallengeRequest.ChallengeRequestStatusChoices.PENDING
    )
    challenge_request.save()

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-status-update",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_reviewer,
        data={
            "status": ChallengeRequest.ChallengeRequestStatusChoices.ACCEPTED
        },
    )
    assert response.status_code == 200
    assert len(mail.outbox) == 1
    # acceptance email to requester
    assert mail.outbox[0].to == [requester1.email]
    assert (
        "We are happy to inform you that your challenge request has been accepted"
        in mail.outbox[0].body
    )
    assert Challenge.objects.count() == 1
    assert Challenge.objects.get().short_name == challenge_request.short_name


@pytest.mark.django_db
def test_budget_field_update(client, challenge_reviewer):
    challenge_request = ChallengeRequestFactory()
    assert challenge_request.expected_number_of_teams == 10
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-budget-update",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_reviewer,
        data={
            "expected_number_of_teams": 500,
            "inference_time_limit_in_minutes": 10,
            "algorithm_selectable_gpu_type_choices": [
                HTMX_BLANK_CHOICE_KEY,
                "A10G",
                "T4",
            ],
            "algorithm_maximum_settable_memory_gb": 32,
            "average_size_of_test_image_in_mb": 10,
            "phase_1_number_of_submissions_per_team": 10,
            "phase_2_number_of_submissions_per_team": 1,
            "phase_1_number_of_test_images": 100,
            "phase_2_number_of_test_images": 500,
            "number_of_tasks": 1,
        },
    )
    assert response.status_code == 200
    challenge_request.refresh_from_db()
    assert challenge_request.expected_number_of_teams == 500


@pytest.mark.django_db
def test_challenge_request_date_check(client):
    user = UserFactory()
    Verification.objects.create(user=user, is_verified=True)

    # start and end dates are required
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-create",
        user=user,
        data={
            "title": "Some title",
            "short_name": "acr6789",
            "contact_email": "test@test.com",
            "abstract": "test",
            "organizers": "test",
            "challenge_setup": "test",
            "data_set": "test",
            "submission_assessment": "test",
            "challenge_publication": "test",
            "code_availability": "test",
            "expected_number_of_teams": 10,
            "algorithm_inputs": "foo",
            "algorithm_outputs": "foo",
            "average_size_of_test_image_in_mb": 1,
            "inference_time_limit_in_minutes": 11,
            "phase_1_number_of_submissions_per_team": 1,
            "phase_2_number_of_submissions_per_team": 1,
            "phase_1_number_of_test_images": 1,
            "phase_2_number_of_test_images": 1,
            "challenge_fee_agreement": True,
        },
    )
    assert response.status_code == 200
    assert response.context["form"].errors == {
        "algorithm_maximum_settable_memory_gb": ["This field is required."],
        "algorithm_selectable_gpu_type_choices": ["This field is required."],
        "end_date": ["This field is required."],
        "number_of_tasks": ["This field is required."],
        "start_date": ["This field is required."],
    }

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-create",
        user=user,
        data={
            "title": "Some title",
            "short_name": "acr6789",
            "contact_email": "test@test.com",
            "abstract": "test",
            "start_date": (now() + timedelta(days=1)).date(),
            "end_date": now().date(),
            "organizers": "test",
            "challenge_setup": "test",
            "data_set": "test",
            "submission_assessment": "test",
            "challenge_publication": "test",
            "code_availability": "test",
            "expected_number_of_teams": 10,
            "algorithm_inputs": "foo",
            "algorithm_outputs": "foo",
            "average_size_of_test_image_in_mb": 1,
            "inference_time_limit_in_minutes": 11,
            "phase_1_number_of_submissions_per_team": 1,
            "phase_2_number_of_submissions_per_team": 1,
            "phase_1_number_of_test_images": 1,
            "phase_2_number_of_test_images": 1,
            "challenge_fee_agreement": True,
        },
    )
    assert response.status_code == 200
    assert response.context["form"].errors == {
        "__all__": ["The start date needs to be before the end date."],
        "algorithm_maximum_settable_memory_gb": ["This field is required."],
        "algorithm_selectable_gpu_type_choices": ["This field is required."],
        "number_of_tasks": ["This field is required."],
    }


@pytest.mark.django_db
def test_challenge_cost_page_permissions(client):
    user, reviewer = UserFactory.create_batch(2)
    assign_perm("challenges.view_challengerequest", reviewer)

    response = get_view_for_user(
        viewname="challenges:cost-overview",
        client=client,
        user=user,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname="challenges:cost-overview",
        client=client,
        user=reviewer,
    )
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    "viewname,add_phase",
    (
        ("pages:create", False),
        ("evaluation:phase-create", False),
        ("evaluation:method-create", True),
        ("evaluation:ground-truth-create", True),
    ),
)
def test_pages_inaccessible_when_inactive(client, viewname, add_phase):
    challenge = ChallengeFactory()
    phase = PhaseFactory(challenge=challenge)

    admin = UserFactory()
    challenge.add_admin(user=admin)

    VerificationFactory(user=admin, is_verified=True)

    def get():
        reverse_kwargs = {"challenge_short_name": challenge.short_name}

        if add_phase:
            reverse_kwargs["slug"] = phase.slug

        return get_view_for_user(
            viewname=viewname,
            client=client,
            user=admin,
            reverse_kwargs=reverse_kwargs,
        )

    assert get().status_code == 200

    challenge.is_active_until = today().date()
    challenge.save()

    assert get().status_code == 403


@pytest.mark.django_db
def test_onboarding_task_list_view_permissions(client):
    ch = ChallengeFactory()
    ch.onboarding_tasks.all().delete()

    admin, participant, user = UserFactory.create_batch(3)
    ch.add_admin(admin)
    ch.add_participant(participant)

    for usr in (participant, user, admin):
        response = get_view_for_user(
            viewname="challenge-onboarding-task-list",
            client=client,
            challenge=ch,
            user=usr,
        )
        assert (
            response.status_code == 200
        ), f"{usr} should be able to view the task list"
        assert len(response.context_data["object_list"]) == 0  # Sanity

    org_task = OnboardingTaskFactory(
        challenge=ch,
        title="A fairly unique onboarding task title, not seen anywhere else",
        responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
    )
    support_task = OnboardingTaskFactory(
        challenge=ch,
        title="A support task title",
        responsible_party=OnboardingTask.ResponsiblePartyChoices.SUPPORT,
    )

    for usr, num_questions in ((participant, 0), (user, 0), (admin, 1)):
        response = get_view_for_user(
            viewname="challenge-onboarding-task-list",
            client=client,
            challenge=ch,
            user=usr,
        )
        assert (
            response.status_code == 200
        ), f"{usr} should still be able to view the question list"
        assert (
            len(response.context_data["object_list"]) == num_questions
        ), f"{usr} should see the correct number of questions"

        if num_questions:
            page_content = response.content.decode()
            assert support_task.title not in page_content
            assert org_task.title in page_content


@pytest.mark.django_db
def test_onboarding_task_list_completion(client):
    ch = ChallengeFactory()
    admin, participant, user = UserFactory.create_batch(3)
    ch.add_admin(admin)
    ch.add_participant(participant)

    org_task = OnboardingTaskFactory(
        challenge=ch,
        responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
    )
    support_task = OnboardingTaskFactory(
        challenge=ch,
        responsible_party=OnboardingTask.ResponsiblePartyChoices.SUPPORT,
    )

    # Sanity, check non-POST
    response = get_view_for_user(
        viewname="challenge-onboarding-task-complete",
        client=client,
        challenge=ch,
        reverse_kwargs={"pk": org_task.pk},
        method=client.get,
        user=admin,
    )
    assert response.status_code == 405, "GET returns method not allowed"

    # Sanity, check non admins
    for usr in (participant, user):
        response = get_view_for_user(
            viewname="challenge-onboarding-task-complete",
            client=client,
            challenge=ch,
            method=client.post,
            reverse_kwargs={"pk": org_task.pk},
            user=usr,
        )
        assert (
            response.status_code == 403
        ), f"{usr} should not be allowed to post completion"

    assert not org_task.complete
    response = get_view_for_user(
        viewname="challenge-onboarding-task-complete",
        client=client,
        challenge=ch,
        method=client.post,
        reverse_kwargs={"pk": org_task.pk},
        data={
            "complete": True,
        },
        user=admin,
        follow=True,
    )
    assert response.status_code == 200, "admin is permitted to post completion"

    org_task.refresh_from_db()
    assert org_task.complete, "Task is marked complete"

    # Can also revert
    response = get_view_for_user(
        viewname="challenge-onboarding-task-complete",
        client=client,
        challenge=ch,
        method=client.post,
        reverse_kwargs={"pk": org_task.pk},
        data={
            "complete": False,
        },
        user=admin,
        follow=True,
    )

    org_task.refresh_from_db()
    assert not org_task.complete, "Task is marked incomplete"

    response = get_view_for_user(
        viewname="challenge-onboarding-task-complete",
        client=client,
        challenge=ch,
        method=client.post,
        reverse_kwargs={"pk": support_task.pk},
        user=admin,
    )
    assert (
        response.status_code == 403
    ), "admin is not allowed to complete support task"
