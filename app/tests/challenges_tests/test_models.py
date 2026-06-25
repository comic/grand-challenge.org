from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from actstream.actions import is_following
from actstream.models import Action
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import ProtectedError
from django.utils.timezone import datetime, now, timedelta

from grandchallenge.challenges.exceptions import InsufficientBudgetError
from grandchallenge.challenges.models import (
    Challenge,
    ChallengeRequest,
    OnboardingTask,
)
from grandchallenge.discussion_forums.models import ForumTopicKindChoices
from grandchallenge.invoices.models import (
    Invoice,
    PaymentStatusChoices,
    PaymentTypeChoices,
)
from grandchallenge.notifications.models import Notification
from tests.discussion_forums_tests.factories import ForumTopicFactory
from tests.factories import (
    ChallengeFactory,
    ChallengeRequestFactory,
    OnboardingTaskFactory,
    UserFactory,
)
from tests.invoices_tests.factories import InvoiceFactory
from tests.invoices_tests.test_models import euro_millicents_to_euros
from tests.organizations_tests.factories import OrganizationFactory


def refresh_challenge(*, challenge: Challenge) -> Challenge:
    return Challenge.objects.with_invoices_with_budget_authorization().get(
        pk=challenge.pk
    )


@pytest.mark.django_db
def test_group_deletion():
    challenge = ChallengeFactory()
    participants_group = challenge.participants_group
    admins_group = challenge.admins_group

    assert participants_group
    assert admins_group

    challenge.page_set.all().delete()
    challenge.phase_set.all().delete()
    Challenge.objects.filter(pk__in=[challenge.pk]).delete()

    with pytest.raises(ObjectDoesNotExist):
        participants_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        admins_group.refresh_from_db()


@pytest.mark.django_db
@pytest.mark.parametrize("group", ["participants_group", "admins_group"])
def test_group_deletion_reverse(group):
    challenge = ChallengeFactory()
    participants_group = challenge.participants_group
    admins_group = challenge.admins_group

    assert participants_group
    assert admins_group

    with pytest.raises(ProtectedError):
        getattr(challenge, group).delete()


@pytest.mark.django_db
def test_default_page_is_created():
    c = ChallengeFactory()
    assert c.page_set.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("group", ("participant", "admin"))
def test_participants_follow_forum(group):
    u = UserFactory()
    c = ChallengeFactory()

    add_method = getattr(c, f"add_{group}")
    remove_method = getattr(c, f"remove_{group}")

    add_method(user=u)
    assert is_following(user=u, obj=c.discussion_forum)

    remove_method(user=u)
    assert is_following(user=u, obj=c.discussion_forum) is False

    # No actions involving the forum should be created
    for i in Action.objects.all():
        assert c.discussion_forum != i.target
        assert c.discussion_forum != i.action_object
        assert c.discussion_forum != i.actor


@pytest.mark.django_db
@pytest.mark.parametrize("group", ("participant", "admin"))
def test_non_posters_notified(
    group, settings, django_capture_on_commit_callbacks
):
    settings.LAMBDA_TASKS_EAGER = True

    p = UserFactory()
    u = UserFactory()
    c = ChallengeFactory()
    c.add_admin(user=p)

    add_method = getattr(c, f"add_{group}")
    add_method(user=u)

    # delete all notifications for easier testing below
    Notification.objects.all().delete()

    with django_capture_on_commit_callbacks(execute=True):
        ForumTopicFactory(
            forum=c.discussion_forum,
            creator=p,
            kind=ForumTopicKindChoices.ANNOUNCE,
        )

    assert u.user_profile.has_unread_notifications is True
    assert p.user_profile.has_unread_notifications is False


@pytest.mark.django_db
def test_is_active_until_set():
    c = ChallengeFactory()
    assert c.is_active_until == today().date() + relativedelta(months=12)


@pytest.mark.parametrize(
    [
        "budget_fields",
        "total_compute_and_storage_costs_euros",
        "total_challenge_price",
    ],
    [
        (
            dict(
                task_ids=[1],
                algorithm_maximum_settable_memory_gb=32,
                algorithm_selectable_gpu_type_choices=["", "T4"],
                average_size_test_case_mb_for_tasks=[10],
                inference_time_average_minutes_for_tasks=[10],
                task_id_for_phases=[1],
                number_of_teams_for_phases=[3],
                number_of_submissions_per_team_for_phases=[10],
                number_of_test_cases_for_phases=[100],
            ),
            706.27,
            6000,
        ),
        (
            dict(
                task_ids=[1],
                algorithm_maximum_settable_memory_gb=32,
                algorithm_selectable_gpu_type_choices=["", "T4"],
                average_size_test_case_mb_for_tasks=[10],
                inference_time_average_minutes_for_tasks=[10],
                task_id_for_phases=[1],
                number_of_teams_for_phases=[10],
                number_of_submissions_per_team_for_phases=[10],
                number_of_test_cases_for_phases=[100],
            ),
            2353.06,
            7500,
        ),
        (
            dict(
                task_ids=[1],
                algorithm_maximum_settable_memory_gb=32,
                algorithm_selectable_gpu_type_choices=["", "A10G", "T4"],
                average_size_test_case_mb_for_tasks=[10],
                inference_time_average_minutes_for_tasks=[10],
                task_id_for_phases=[1],
                number_of_teams_for_phases=[10],
                number_of_submissions_per_team_for_phases=[10],
                number_of_test_cases_for_phases=[100],
            ),
            3553.30,
            9000,
        ),
        (
            dict(
                task_ids=[1, 2],
                algorithm_maximum_settable_memory_gb=32,
                algorithm_selectable_gpu_type_choices=["", "T4"],
                average_size_test_case_mb_for_tasks=[10, 100],
                inference_time_average_minutes_for_tasks=[5, 10],
                task_id_for_phases=[1, 1, 2, 2],
                number_of_submissions_per_team_for_phases=[10, 1, 10, 1],
                number_of_teams_for_phases=[3, 3, 3, 3],
                number_of_test_cases_for_phases=[3, 100, 3, 100],
            ),
            363.23,
            6000,
        ),
    ],
)
@pytest.mark.django_db
def test_total_challenge_cost(
    settings,
    budget_fields,
    total_compute_and_storage_costs_euros,
    total_challenge_price,
):
    settings.COMPONENTS_DEFAULT_BACKEND = "grandchallenge.components.backends.amazon_sagemaker_training.AmazonSageMakerTrainingExecutor"

    request = ChallengeRequestFactory(
        **budget_fields,
    )

    assert (
        pytest.approx(request.total_compute_and_storage_costs_euros, abs=0.01)
        == total_compute_and_storage_costs_euros
    )
    assert request.total_challenge_price == total_challenge_price


@pytest.mark.django_db
def test_total_challenge_price_user_exempt_from_base_cost():
    user_exempt, user_normal = UserFactory.create_batch(2)
    request_exempt = ChallengeRequestFactory(
        creator=user_exempt,
    )
    request_normal = ChallengeRequestFactory(
        creator=user_normal,
    )
    organisation = OrganizationFactory(exempt_from_base_costs=True)
    organisation.members_group.user_set.add(user_exempt)

    assert (
        request_exempt.total_compute_and_storage_costs_euros
        == request_normal.total_compute_and_storage_costs_euros
    )
    assert (
        request_normal.total_challenge_price
        - request_exempt.total_challenge_price
        == 5000
    )


def test_challenge_request_budget_calculation(settings):
    settings.COMPONENTS_DEFAULT_BACKEND = "grandchallenge.components.backends.amazon_sagemaker_training.AmazonSageMakerTrainingExecutor"
    challenge_request = ChallengeRequest(
        task_ids=[1],
        algorithm_maximum_settable_memory_gb=32,
        algorithm_selectable_gpu_type_choices=["", "T4"],
        average_size_test_case_mb_for_tasks=[100],
        inference_time_average_minutes_for_tasks=[10],
        task_id_for_phases=[1, 1],
        number_of_teams_for_phases=[10, 10],
        number_of_submissions_per_team_for_phases=[100, 10],
        number_of_test_cases_for_phases=[100, 500],
    )

    costs_for_phases = [
        {
            # "name": "Phase 1",
            "compute_costs_euros_per_hour": 1.17,
            "compute_time_hours": 16667,
            "compute_costs_euros": 19500.39,
            "data_storage_size_gb": 10,
            "data_storage_costs_euros": 6.70,
            "compute_and_storage_costs_euros": 19507.09,
        },
        {
            # "name": "Phase 2",
            "compute_costs_euros_per_hour": 1.17,
            "compute_time_hours": 8333,
            "compute_costs_euros": 9749.61,
            "data_storage_size_gb": 49,
            "data_storage_costs_euros": 32.83,
            "compute_and_storage_costs_euros": 9782.44,
        },
    ]
    assert challenge_request.storage_costs_euros_per_gb() == 0.67
    for i_phase in range(2):
        assert (
            costs_for_phases[i_phase]["compute_and_storage_costs_euros"]
            == costs_for_phases[i_phase]["compute_costs_euros"]
            + costs_for_phases[i_phase]["data_storage_costs_euros"]
        )
        for k, v in costs_for_phases[i_phase].items():
            assert (
                pytest.approx(
                    getattr(challenge_request, k + "_for_phases")[i_phase],
                    abs=0.01,
                )
                == v
            )
    assert challenge_request.total_docker_storage_size_gb == 6 * 10 * 100
    assert (
        pytest.approx(
            challenge_request.total_docker_storage_costs_euros,
            abs=0.01,
        )
        == 4020.00
    )
    assert (
        pytest.approx(
            challenge_request.compute_costs_euros_for_tasks[0],
            abs=0.01,
        )
        == 29250.00
    )
    assert (
        pytest.approx(
            challenge_request.storage_costs_euros_for_tasks[0],
            abs=0.01,
        )
        == 4059.53
    )
    assert (
        pytest.approx(
            challenge_request.total_compute_and_storage_costs_euros,
            abs=0.01,
        )
        == pytest.approx(
            challenge_request.compute_and_storage_costs_euros_for_tasks[0],
            abs=0.01,
        )
        == pytest.approx(
            challenge_request.compute_costs_euros_for_tasks[0]
            + challenge_request.storage_costs_euros_for_tasks[0],
            abs=0.01,
        )
        == 33309.53
    )

    for i_phase in range(2):
        assert (
            challenge_request.compute_and_storage_costs_euros_for_phases[
                i_phase
            ]
            == challenge_request.compute_costs_euros_for_phases[i_phase]
            + challenge_request.data_storage_costs_euros_for_phases[i_phase]
        )

    assert (
        challenge_request.total_compute_and_storage_costs_euros
        == challenge_request.compute_and_storage_costs_euros_for_phases[0]
        + challenge_request.compute_and_storage_costs_euros_for_phases[1]
        + challenge_request.total_docker_storage_costs_euros
    )


@pytest.mark.django_db
def test_onboarding_tasks_registering_completion_time():
    ch = ChallengeFactory()
    task = OnboardingTaskFactory(challenge=ch, complete=False)

    # Sanity
    assert not task.complete
    assert task.completed_at is None

    fake_now = now()
    with patch("grandchallenge.challenges.models.now", return_value=fake_now):
        task.complete = True
        task.save()

    task.refresh_from_db()
    assert task.complete
    assert task.completed_at == fake_now

    fresh_task = OnboardingTaskFactory(challenge=ch, complete=True)

    assert fresh_task.complete
    assert fresh_task.created == fresh_task.completed_at


@pytest.mark.django_db
@pytest.mark.parametrize(
    "deadline, mock_now, expected_is_overdue, expected_is_overdue_soon",
    [
        # Test case 1: Task deadline is far away, so it's neither overdue nor almost overdue
        (
            datetime(2025, 1, 30, 11, 0, 0, tzinfo=ZoneInfo("UTC")),
            datetime(2025, 1, 29, 11, 0, 0, tzinfo=ZoneInfo("UTC")),
            False,
            False,
        ),
        # Test case 2: Task is almost overdue (within the 1-hour cutoff)
        (
            datetime(2025, 1, 29, 12, 0, 0, tzinfo=ZoneInfo("UTC")),
            datetime(2025, 1, 29, 11, 30, 0, tzinfo=ZoneInfo("UTC")),
            False,
            True,
        ),
        # Test case 3: Task is overdue
        (
            datetime(2025, 1, 29, 11, 0, 0, tzinfo=ZoneInfo("UTC")),
            datetime(2025, 1, 29, 12, 0, 0, tzinfo=ZoneInfo("UTC")),
            True,
            False,
        ),
    ],
)
@patch(
    "grandchallenge.challenges.models.settings.CHALLENGE_ONBOARDING_TASKS_OVERDUE_SOON_CUTOFF",
    new=timedelta(hours=1),
)
def test_onboarding_tasks_overdue_status_annotations(
    deadline,
    mock_now,
    expected_is_overdue,
    expected_is_overdue_soon,
    mocker,
):
    task = OnboardingTaskFactory(deadline=deadline)

    mocker.patch("grandchallenge.challenges.models.now", return_value=mock_now)

    task = OnboardingTask.objects.with_overdue_status().get(pk=task.pk)
    assert task.is_overdue == expected_is_overdue
    assert task.is_overdue_soon == expected_is_overdue_soon


@pytest.mark.django_db
def test_default_onboarding_tasks_creation():
    challenge = ChallengeFactory()

    # Expected task details
    expected_tasks = {
        ("Create Phases", "ORG"),
        ("Define Inputs and Outputs", "ORG"),
        ("Plan Onboarding Meeting", "SUP"),
        ("Have Onboarding Meeting", "ORG"),
        ("Create Archives", "SUP"),
        ("Upload Data to Archives", "ORG"),
        ("Create Example Algorithm", "ORG"),
        ("Create Evaluation Method", "ORG"),
        ("Configure Scoring", "ORG"),
        ("Test Evaluation", "ORG"),
    }

    tasks = list(OnboardingTask.objects.filter(challenge=challenge))

    assert len(tasks) == len(
        expected_tasks
    ), "Unexpected number of onboarding tasks."

    tasks_title_and_responsible_party = {
        (task.title, task.responsible_party) for task in tasks
    }

    assert tasks_title_and_responsible_party == expected_tasks


@pytest.mark.django_db
def test_discussion_forum_permissions():
    challenge = ChallengeFactory(display_forum_link=True)
    admin, participant = UserFactory.create_batch(2)
    challenge.add_admin(admin)
    challenge.add_participant(participant)

    assert challenge.discussion_forum
    assert admin.has_perm("view_forum", challenge.discussion_forum)
    assert participant.has_perm("view_forum", challenge.discussion_forum)
    assert admin.has_perm("create_forum_topic", challenge.discussion_forum)
    assert admin.has_perm(
        "create_sticky_and_announcement_topic", challenge.discussion_forum
    )
    assert participant.has_perm(
        "create_forum_topic", challenge.discussion_forum
    )
    assert not participant.has_perm(
        "create_sticky_and_announcement_topic", challenge.discussion_forum
    )

    challenge.display_forum_link = False
    challenge.save()

    assert not admin.has_perm("view_forum", challenge.discussion_forum)
    assert not participant.has_perm("view_forum", challenge.discussion_forum)
    assert not admin.has_perm("create_forum_topic", challenge.discussion_forum)
    assert not participant.has_perm(
        "create_forum_topic", challenge.discussion_forum
    )
    assert not admin.has_perm(
        "create_sticky_and_announcement_topic", challenge.discussion_forum
    )
    assert not participant.has_perm(
        "create_sticky_and_announcement_topic", challenge.discussion_forum
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "data,expected_error",
    [
        # Valid submission with DOI - should pass
        (
            {
                "start_date": datetime.now() + timedelta(days=1),
                "end_date": datetime.now() + timedelta(days=2),
                "organizers": "foo",
                "challenge_setup": "bar",
                "structured_challenge_submission_doi": "10.5281/zenodo.6362337",
                "challenge_fee_agreement": True,
            },
            None,
        ),
        # Valid submission with all challenge details fields - should pass
        (
            {
                "start_date": datetime.now() + timedelta(days=1),
                "end_date": datetime.now() + timedelta(days=2),
                "organizers": "foo",
                "challenge_setup": "bar",
                "data_set": "dataset info",
                "data_license": True,
                "submission_assessment": "assessment info",
                "challenge_publication": "publication info",
                "code_availability": "code availability info",
                "algorithm_inputs": "input description",
                "algorithm_outputs": "output description",
                "challenge_fee_agreement": True,
            },
            None,
        ),
        # Valid submission with all challenge details fields - but data license extra is missing
        (
            {
                "start_date": datetime.now() + timedelta(days=1),
                "end_date": datetime.now() + timedelta(days=2),
                "organizers": "foo",
                "challenge_setup": "bar",
                "data_set": "dataset info",
                "data_license": True,
                "submission_assessment": "assessment info",
                "challenge_publication": "publication info",
                "code_availability": "code availability info",
                "algorithm_inputs": "input description",
                "algorithm_outputs": "output description",
                "challenge_fee_agreement": True,
            },
            None,
        ),
        # Missing data license extra
        (
            {
                "start_date": datetime.now() + timedelta(days=1),
                "end_date": datetime.now() + timedelta(days=2),
                "organizers": "foo",
                "challenge_setup": "bar",
                "data_set": "dataset info",
                "data_license": False,
                "submission_assessment": "assessment info",
                "challenge_publication": "publication info",
                "code_availability": "code availability info",
                "algorithm_inputs": "input description",
                "algorithm_outputs": "output description",
                "challenge_fee_agreement": True,
            },
            "You need to explain why you are not willing/able to use a CC-BY license.",
        ),
        # Missing required fields - should fail
        (
            {
                "start_date": datetime.now() + timedelta(days=1),
                "end_date": datetime.now() + timedelta(days=2),
                "challenge_fee_agreement": True,
            },
            "The following fields are required to submit a challenge request: Organizers, Challenge Setup",
        ),
        # Start date after end date - should fail
        (
            {
                "start_date": datetime.now() + timedelta(days=10),
                "end_date": datetime.now() + timedelta(days=2),
                "organizers": "foo",
                "challenge_setup": "bar",
                "structured_challenge_submission_doi": "10.5281/zenodo.6362337",
                "challenge_fee_agreement": True,
            },
            "The start date needs to be before the end date",
        ),
        # Missing challenge details without DOI/form - should fail
        (
            {
                "start_date": datetime.now() + timedelta(days=1),
                "end_date": datetime.now() + timedelta(days=2),
                "organizers": "foo",
                "challenge_setup": "bar",
                "challenge_fee_agreement": True,
            },
            "Either a structured challenge submission form needs to be uploaded or the following fields are required",
        ),
        # Missing challenge fee agreement - should fail
        (
            {
                "start_date": datetime.now() + timedelta(days=1),
                "end_date": datetime.now() + timedelta(days=2),
                "organizers": "foo",
                "challenge_setup": "bar",
                "structured_challenge_submission_doi": "10.5281/zenodo.6362337",
                "challenge_fee_agreement": False,
            },
            "You need to agree to the challenge pricing policy to submit a challenge request",
        ),
        # Only some challenge detail fields present without DOI - should fail
        (
            {
                "start_date": datetime.now() + timedelta(days=1),
                "end_date": datetime.now() + timedelta(days=2),
                "organizers": "foo",
                "challenge_setup": "bar",
                "data_set": "dataset info",
                "algorithm_inputs": "input description",
                "challenge_fee_agreement": True,
            },
            "Either a structured challenge submission form needs to be uploaded or the following fields are required",
        ),
    ],
)
def test_challenge_request_submission_cleaning(data, expected_error):
    challenge_request = ChallengeRequest.objects.create(
        creator=UserFactory(),
        title="foo",
        short_name="foo",
        abstract="bar",
        contact_email="test@example.test",
        **data,
    )

    # Should not raise any validation error at this point since the request is not being submitted yet
    challenge_request.clean()

    challenge_request.status = (
        ChallengeRequest.ChallengeRequestStatusChoices.PENDING
    )

    if expected_error is None:
        # Should not raise any validation error
        challenge_request.clean()
        assert challenge_request.can_be_submitted
    else:
        # Should raise a ValidationError containing the expected error message
        with pytest.raises(ValidationError) as exc_info:
            challenge_request.clean()
        error_messages = str(exc_info.value)
        assert expected_error in error_messages


@pytest.mark.django_db
@pytest.mark.parametrize(
    "data,expected_error",
    (
        (
            {
                "task_ids": [1, 2],
                "algorithm_maximum_settable_memory_gb": 32,
                "algorithm_selectable_gpu_type_choices": ["", "T4"],
                "average_size_test_case_mb_for_tasks": [10, 100],
                "inference_time_average_minutes_for_tasks": [5, 10],
                "task_id_for_phases": [1, 1, 2, 2],
                "number_of_submissions_per_team_for_phases": [10, 1, 10, 1],
                "number_of_teams_for_phases": [10, 10, 10, 10],
                "number_of_test_cases_for_phases": [3, 100, 3, 100],
            },
            None,
        ),
        (
            {  # Note, missing task_ids
                "algorithm_maximum_settable_memory_gb": 32,
                "algorithm_selectable_gpu_type_choices": ["", "T4"],
                "average_size_test_case_mb_for_tasks": [10, 100],
                "inference_time_average_minutes_for_tasks": [5, 10],
                "task_id_for_phases": [1, 1, 2, 2],
                "number_of_submissions_per_team_for_phases": [10, 1, 10, 1],
                "number_of_teams_for_phases": [10, 10, 10, 10],
                "number_of_test_cases_for_phases": [3, 100, 3, 100],
            },
            "The following fields are required to accept a challenge request: Task Ids",
        ),
    ),
)
def test_challenge_request_accept_cleaning(data, expected_error):
    challenge_request = ChallengeRequest.objects.create(
        creator=UserFactory(),
        title="foo",
        short_name="foo",
        abstract="bar",
        contact_email="test@example.test",
        start_date=datetime.now() + timedelta(days=1),
        end_date=datetime.now() + timedelta(days=2),
        organizers="foo",
        challenge_setup="bar",
        structured_challenge_submission_doi="10.5281/zenodo.6362337",
        challenge_fee_agreement=True,
        status=ChallengeRequest.ChallengeRequestStatusChoices.PENDING,
        submitted_on=now(),
        **data,
    )

    challenge_request.status = (
        ChallengeRequest.ChallengeRequestStatusChoices.ACCEPTED
    )

    if expected_error is None:
        # Should not raise any validation error
        challenge_request.clean()
    else:
        # Should raise a ValidationError containing the expected error message
        with pytest.raises(ValidationError) as exc_info:
            challenge_request.clean()
        error_messages = str(exc_info.value)
        assert expected_error in error_messages


@pytest.mark.django_db
def test_challenge_request_submitted_field_set_on_status_update():
    challenge_request = ChallengeRequestFactory(
        status=ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
        submitted_on=None,
    )

    # Initially submitted should be None
    assert challenge_request.submitted_on is None

    # Submit the request by updating status from DRAFT to PENDING
    challenge_request.status = (
        ChallengeRequest.ChallengeRequestStatusChoices.PENDING
    )
    challenge_request.save()

    # Refresh and check that submitted is now set
    challenge_request.refresh_from_db()
    assert challenge_request.submitted_on is not None
    assert (
        challenge_request.status
        == ChallengeRequest.ChallengeRequestStatusChoices.PENDING
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "challenge_admin",
    (True, False),
    ids=["admin", "not_admin"],
)
@pytest.mark.parametrize(
    "challenge_participant",
    (True, False),
    ids=["participant", "not_participant"],
)
def test_challenge_queryset_with_user_roles(
    challenge_admin, challenge_participant
):
    challenge = ChallengeFactory()
    user = UserFactory()

    if challenge_admin:
        challenge.add_admin(user)
    if challenge_participant:
        challenge.add_participant(user)

    qs = Challenge.objects.with_user_roles(user=user)
    result = qs.get(pk=challenge.pk)

    assert result.user_is_challenge_admin is challenge_admin
    assert result.user_is_challenge_participant is challenge_participant


@pytest.mark.django_db
def test_challenge_queryset_with_user_roles_multiple_challenges():
    challenge1 = ChallengeFactory()
    challenge2 = ChallengeFactory()
    challenge3 = ChallengeFactory()
    challenge4 = ChallengeFactory()
    user = UserFactory()

    challenge2.add_participant(user)
    challenge3.add_admin(user)
    challenge4.add_participant(user)
    challenge4.add_admin(user)

    qs = Challenge.objects.with_user_roles(user=user)
    assert qs.count() == 4
    result = {ch.pk: ch for ch in qs}

    # Non-member
    assert result[challenge1.pk].user_is_challenge_admin is False
    assert result[challenge1.pk].user_is_challenge_participant is False

    # Participant
    assert result[challenge2.pk].user_is_challenge_admin is False
    assert result[challenge2.pk].user_is_challenge_participant is True

    # Editor
    assert result[challenge3.pk].user_is_challenge_admin is True
    assert result[challenge3.pk].user_is_challenge_participant is False

    # Both
    assert result[challenge4.pk].user_is_challenge_admin is True
    assert result[challenge4.pk].user_is_challenge_participant is True


@pytest.mark.django_db
def test_utilization_invoice():
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    challenge = (
        Challenge.objects.with_invoices_with_budget_authorization().get(
            pk=challenge.pk
        )
    )
    assert challenge.utilization_invoice == invoice


@pytest.mark.django_db
def test_utilization_invoice_no_invoice():
    challenge = ChallengeFactory()
    challenge = (
        Challenge.objects.with_invoices_with_budget_authorization().get(
            pk=challenge.pk
        )
    )
    with pytest.raises(InsufficientBudgetError):
        challenge.utilization_invoice


@pytest.mark.django_db
def test_utilization_invoice_raises_on_negative_balance():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_cost_euro_millicents=2 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    challenge = (
        Challenge.objects.with_invoices_with_budget_authorization().get(
            pk=challenge.pk
        )
    )
    with pytest.raises(InsufficientBudgetError):
        challenge.utilization_invoice


@pytest.mark.django_db
def test_utilization_invoice_raises_on_zero_balance():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_cost_euro_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    challenge = (
        Challenge.objects.with_invoices_with_budget_authorization().get(
            pk=challenge.pk
        )
    )
    with pytest.raises(InsufficientBudgetError):
        challenge.utilization_invoice


@pytest.mark.django_db
def test_utilization_invoice_ignores_invoices_with_negative_balance():
    challenge = ChallengeFactory()

    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_cost_euro_millicents=1000 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )

    challenge = (
        Challenge.objects.with_invoices_with_budget_authorization().get(
            pk=challenge.pk
        )
    )
    challenge.utilization_invoice


@pytest.mark.django_db
def test_budget_properties():
    challenge = ChallengeFactory()

    challenge = (
        Challenge.objects.with_invoices_with_budget_authorization().get(
            pk=challenge.pk
        )
    )
    assert challenge.available_compute_cost_euro_millicents == 0
    assert challenge.approved_compute_cost_euro_millicents == 0
    assert challenge.consumed_compute_cost_euro_millicents == 0
    assert challenge.write_off_compute_cost_euro_millicents == 0
    assert challenge.percent_active_compute_budget_consumed is None

    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=10,
        compute_cost_euro_millicents=6 * 1000 * 100,
    )

    challenge = (
        Challenge.objects.with_invoices_with_budget_authorization().get(
            pk=challenge.pk
        )
    )

    assert challenge.available_compute_cost_euro_millicents == 4 * 1000 * 100
    assert challenge.approved_compute_cost_euro_millicents == 10 * 1000 * 100
    assert challenge.consumed_compute_cost_euro_millicents == 6 * 1000 * 100
    assert challenge.write_off_compute_cost_euro_millicents == 0
    assert challenge.percent_active_compute_budget_consumed == 60


@pytest.mark.django_db
def test_total_costs_properties():
    challenge = ChallengeFactory(
        size_in_storage=30 * 1024**3,  # 30 GB
        size_in_registry=70 * 1024**3,  # 70 GB
    )
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=200,
        storage_costs_euros=100,
        compute_cost_euro_millicents=10 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=PaymentStatusChoices.PAID,
    )
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=100,
        storage_costs_euros=50,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=PaymentStatusChoices.PAID,
    )
    # This one should not count (cancelled)
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=500,
        storage_costs_euros=250,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=PaymentStatusChoices.CANCELLED,
    )

    challenge = refresh_challenge(challenge=challenge)

    assert (
        euro_millicents_to_euros(
            euro_millicents=challenge.total_projected_storage_cost_euro_millicents
        )
        == 67
    )
    assert (
        euro_millicents_to_euros(
            euro_millicents=challenge.compute_cost_euro_millicents
        )
        == 10
    )
    assert (
        euro_millicents_to_euros(
            euro_millicents=challenge.total_paid_compute_costs_euro_millicents
        )
        == 300
    )
    assert (
        euro_millicents_to_euros(
            euro_millicents=challenge.total_paid_storage_costs_euro_millicents
        )
        == 150
    )
    assert (
        euro_millicents_to_euros(
            euro_millicents=challenge.unpaid_storage_costs_euro_millicents
        )
        == 0
    )
    assert round(challenge.compute_cost_share, 2) == 0.13


@pytest.mark.django_db
def test_total_projected_storage_costs_beyond_prepaid_amount():
    challenge = ChallengeFactory(
        size_in_storage=30 * 1024**3,  # 30 GB
        size_in_registry=70 * 1024**3,  # 70 GB
    )
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=200,
        storage_costs_euros=1,  # does not cover storage costs
        compute_cost_euro_millicents=10 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=PaymentStatusChoices.PAID,
    )

    challenge = refresh_challenge(challenge=challenge)

    assert (
        euro_millicents_to_euros(
            euro_millicents=challenge.total_projected_storage_cost_euro_millicents
        )
        == 67
    )
    assert (
        euro_millicents_to_euros(
            euro_millicents=challenge.total_paid_storage_costs_euro_millicents
        )
        == 1
    )
    assert (
        euro_millicents_to_euros(
            euro_millicents=challenge.unpaid_storage_costs_euro_millicents
        )
        == 66
    )


@pytest.mark.parametrize(
    "payment_type, payment_status",
    (
        (PaymentTypeChoices.PREPAID, PaymentStatusChoices.INITIALIZED),
        (PaymentTypeChoices.PREPAID, PaymentStatusChoices.REQUESTED),
        (PaymentTypeChoices.PREPAID, PaymentStatusChoices.ISSUED),
        (PaymentTypeChoices.PREPAID, PaymentStatusChoices.CANCELLED),
        (PaymentTypeChoices.COMPLIMENTARY, PaymentStatusChoices.CANCELLED),
        (PaymentTypeChoices.POSTPAID, PaymentStatusChoices.INITIALIZED),
        (PaymentTypeChoices.POSTPAID, PaymentStatusChoices.REQUESTED),
        (PaymentTypeChoices.POSTPAID, PaymentStatusChoices.ISSUED),
        (PaymentTypeChoices.POSTPAID, PaymentStatusChoices.CANCELLED),
    ),
)
@pytest.mark.django_db
def test_postpaid_calculation_ignores_other_nonpaid_invoices(
    payment_type, payment_status
):
    challenge = ChallengeFactory()
    # prepaid paid invoice
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=100,
        storage_costs_euros=100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=PaymentStatusChoices.PAID,
    )
    # Postpaid invoice (initialized)
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=10,
        storage_costs_euros=10,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=PaymentStatusChoices.INITIALIZED,
    )
    # other invoice which should be ignored
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=100,
        storage_costs_euros=100,
        payment_type=payment_type,
        payment_status=payment_status,
    )
    challenge = refresh_challenge(challenge=challenge)

    assert (
        euro_millicents_to_euros(
            euro_millicents=challenge.total_paid_storage_costs_euro_millicents
        )
        == 100
    )
    assert (
        euro_millicents_to_euros(
            euro_millicents=challenge.total_paid_compute_costs_euro_millicents
        )
        == 100
    )


@pytest.mark.parametrize(
    "already_paid_amount, to_be_paid_amount",
    (
        (10, 57),
        (100, 0),
    ),
)
@pytest.mark.django_db
def test_unpaid_storage_costs_euro_millicents_capped_at_0(
    already_paid_amount, to_be_paid_amount
):
    challenge = ChallengeFactory(
        size_in_storage=30 * 1024**3,  # 30 GB
        size_in_registry=70 * 1024**3,  # 70 GB, ~67 EUR total storage
    )
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=100,
        storage_costs_euros=already_paid_amount,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=PaymentStatusChoices.PAID,
    )
    # Postpaid invoice (initialized)
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=10,
        storage_costs_euros=10,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=PaymentStatusChoices.INITIALIZED,
    )
    challenge = refresh_challenge(challenge=challenge)

    assert (
        euro_millicents_to_euros(
            euro_millicents=challenge.unpaid_storage_costs_euro_millicents
        )
        == to_be_paid_amount
    )


@pytest.mark.django_db
def test_compute_cost_share_none_when_no_utilization():
    challenge = ChallengeFactory(
        size_in_storage=0,  # 0 GB
        size_in_registry=0,  # 0 GB
    )

    challenge = refresh_challenge(challenge=challenge)

    # No storage and no compute means total utilization is 0
    assert challenge.compute_cost_share is None


@pytest.mark.django_db
def test_compute_cost_share_ratio():
    challenge = ChallengeFactory(
        size_in_storage=50 * 1024**3,  # 50 GB
        size_in_registry=50 * 1024**3,  # 50 GB
    )
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=100,
        storage_costs_euros=50,
        compute_cost_euro_millicents=40 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=PaymentStatusChoices.PAID,
    )

    challenge = refresh_challenge(challenge=challenge)

    # compute_cost_share = compute / (compute + storage)
    expected_share = challenge.compute_cost_euro_millicents / (
        challenge.compute_cost_euro_millicents
        + challenge.total_projected_storage_cost_euro_millicents
    )
    assert challenge.compute_cost_share == expected_share
    # Share should be between 0 and 1
    assert 0 < challenge.compute_cost_share < 1


@pytest.mark.django_db
def test_active_budget_properties():
    challenge = ChallengeFactory()

    challenge = (
        Challenge.objects.with_invoices_with_budget_authorization().get(
            pk=challenge.pk
        )
    )
    assert challenge.active_available_compute_cost_euro_millicents == 0
    assert challenge.active_approved_compute_cost_euro_millicents == 0
    assert challenge.active_consumed_compute_cost_euro_millicents == 0

    InvoiceFactory(  # Active invoice
        challenge=challenge,
        compute_costs_euros=10,
        compute_cost_euro_millicents=6 * 1000 * 100,
    )

    challenge = (
        Challenge.objects.with_invoices_with_budget_authorization().get(
            pk=challenge.pk
        )
    )

    assert (
        challenge.active_available_compute_cost_euro_millicents
        == 4 * 1000 * 100
    )
    assert (
        challenge.active_approved_compute_cost_euro_millicents
        == 10 * 1000 * 100
    )
    assert (
        challenge.active_consumed_compute_cost_euro_millicents
        == 6 * 1000 * 100
    )

    InvoiceFactory(  # Active invoice, should not be ignored in active budget properties
        challenge=challenge,
        compute_costs_euros=10,
        compute_cost_euro_millicents=6 * 1000 * 100,
    )
    InvoiceFactory(  # Expired invoice, should be ignored in active budget properties
        challenge=challenge,
        compute_costs_euros=10,
        compute_cost_euro_millicents=6 * 1000 * 100,
        expires_on=now() - timedelta(days=1),
    )

    challenge = (
        Challenge.objects.with_invoices_with_budget_authorization().get(
            pk=challenge.pk
        )
    )

    assert (
        challenge.active_available_compute_cost_euro_millicents
        == 4 * 2 * 1000 * 100
    )
    assert (
        challenge.active_approved_compute_cost_euro_millicents
        == 10 * 2 * 1000 * 100
    )
    assert (
        challenge.active_consumed_compute_cost_euro_millicents
        == 6 * 2 * 1000 * 100
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "choices,should_raise",
    [
        (["", "T4"], False),
        (["", "A10G", "T4"], False),
        (["", "A100", "A10G", "T4"], False),
        (["T4"], True),  # missing NO_GPU
        (["A10G", "T4"], True),  # missing NO_GPU
        (["", "A10G"], True),  # A10G without T4
        (["", "A100", "T4"], True),  # A100 without A10G
        (["", "A100"], True),  # A100 without A10G and T4
    ],
)
def test_challenge_request_algorithm_selectable_gpu_type_choices_validation(
    choices, should_raise
):
    challenge_request = ChallengeRequest(
        algorithm_selectable_gpu_type_choices=choices,
    )

    if should_raise:
        with pytest.raises(ValidationError):
            challenge_request.clean()
    else:
        challenge_request.clean()
