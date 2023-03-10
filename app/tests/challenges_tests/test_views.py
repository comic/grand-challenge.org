from datetime import timedelta

import pytest
from django.core import mail
from django.utils.timezone import now
from guardian.shortcuts import assign_perm

from grandchallenge.challenges.models import Challenge, ChallengeRequest
from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.models import Verification
from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import ChallengeFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_external_challenge_buttons(client):
    create_url = reverse("challenges:external-create")
    list_url = reverse("challenges:external-list")

    response = get_view_for_user(
        client=client, viewname="challenges:combined-list"
    )

    assert create_url not in response.rendered_content
    assert list_url not in response.rendered_content

    user = UserFactory()

    response = get_view_for_user(
        client=client, viewname="challenges:combined-list", user=user
    )

    assert create_url not in response.rendered_content
    assert list_url not in response.rendered_content

    assign_perm("challenges.change_externalchallenge", user)

    response = get_view_for_user(
        client=client, viewname="challenges:combined-list", user=user
    )

    assert create_url in response.rendered_content
    assert list_url in response.rendered_content


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
    phase1 = ch.phase_set.first()
    phase2 = PhaseFactory(challenge=ch)
    u = UserFactory()

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
    challenge_request,
):
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
def test_budget_field_update(client, challenge_request, challenge_reviewer):
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
    assert (
        '<span id="error_1_id_start_date" class="invalid-feedback"><strong>This field is required.</strong></span>'
        in response.rendered_content
    )
    assert (
        '<span id="error_1_id_end_date" class="invalid-feedback"><strong>This field is required.</strong></span>'
        in response.rendered_content
    )

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
    assert (
        "The start date needs to be before the end date"
        in response.rendered_content
    )


@pytest.mark.parametrize(
    "viewname, reverse_kwargs, data",
    [
        ("challenges:cost-overview", None, None),
        ("challenges:costs-per-phase", True, None),
        ("challenges:challenge-cost-row", True, None),
        ("challenges:costs-per-year", None, {"year": "2021"}),
        ("challenges:year-cost-row", None, {"year": "2021"}),
    ],
)
@pytest.mark.django_db
def test_challenge_cost_page_permissions(
    client, viewname, reverse_kwargs, data
):
    user, reviewer = UserFactory.create_batch(2)
    assign_perm("challenges.view_challengerequest", reviewer)
    if reverse_kwargs:
        challenge = ChallengeFactory()
        reverse_kwargs_for_view = {"pk": challenge.pk}
    else:
        reverse_kwargs_for_view = None
    response = get_view_for_user(
        viewname=viewname,
        reverse_kwargs=reverse_kwargs_for_view,
        client=client,
        user=user,
        data=data,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname=viewname,
        reverse_kwargs=reverse_kwargs_for_view,
        client=client,
        user=reviewer,
        data=data,
    )
    assert response.status_code == 200
