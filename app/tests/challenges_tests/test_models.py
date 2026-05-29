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
from grandchallenge.invoices.models import Invoice, PaymentTypeChoices
from grandchallenge.notifications.models import Notification
from tests.discussion_forums_tests.factories import ForumTopicFactory
from tests.factories import (
    ChallengeFactory,
    ChallengeRequestFactory,
    OnboardingTaskFactory,
    UserFactory,
)
from tests.invoices_tests.factories import InvoiceFactory
from tests.organizations_tests.factories import OrganizationFactory


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
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

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
                algorithm_maximum_settable_memory_gb_for_tasks=[32],
                algorithm_selectable_gpu_type_choices_for_tasks=[["", "T4"]],
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
                algorithm_maximum_settable_memory_gb_for_tasks=[32],
                algorithm_selectable_gpu_type_choices_for_tasks=[["", "T4"]],
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
                algorithm_maximum_settable_memory_gb_for_tasks=[32],
                algorithm_selectable_gpu_type_choices_for_tasks=[
                    ["", "A10G", "T4"]
                ],
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
                algorithm_maximum_settable_memory_gb_for_tasks=[32, 32],
                algorithm_selectable_gpu_type_choices_for_tasks=[
                    ["", "T4"],
                    ["", "T4"],
                ],
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
        algorithm_maximum_settable_memory_gb_for_tasks=[32],
        algorithm_selectable_gpu_type_choices_for_tasks=[["", "T4"]],
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
    assert challenge_request.storage_costs_euros_per_gb == 0.67
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
                "algorithm_maximum_settable_memory_gb_for_tasks": [32, 32],
                "algorithm_selectable_gpu_type_choices_for_tasks": [
                    ["", "T4"],
                    ["", "A10G", "T4"],
                ],
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
                "algorithm_maximum_settable_memory_gb_for_tasks": [32, 32],
                "algorithm_selectable_gpu_type_choices_for_tasks": [
                    ["", "T4"],
                    ["", "A10G", "T4"],
                ],
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
def test_active_invoice():
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    assert challenge.active_invoice == invoice


@pytest.mark.django_db
def test_active_invoice_no_invoice():
    challenge = ChallengeFactory()
    with pytest.raises(InsufficientBudgetError):
        challenge.active_invoice


@pytest.mark.django_db
def test_active_invoice_raises_on_negative_balance():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_cost_euro_millicents=2 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    with pytest.raises(InsufficientBudgetError):
        challenge.active_invoice


@pytest.mark.django_db
def test_active_invoice_raises_on_zero_balance():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_cost_euro_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    with pytest.raises(InsufficientBudgetError):
        challenge.active_invoice


@pytest.mark.django_db
def test_active_invoice_orders_by_expiry():
    challenge = ChallengeFactory()

    _fixed_now = now()

    invoice0 = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
        expires_on=_fixed_now + timedelta(10),
    )
    invoice1 = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
        expires_on=_fixed_now + timedelta(10),
    )

    # All things being equal, use created time to determine order, so invoice0 should be active as it was created first
    assert challenge.active_invoice == invoice0

    invoice1.expires_on = _fixed_now + timedelta(5)
    invoice1.save()
    assert invoice1.expires_on < invoice0.expires_on, "Sanity"
    assert challenge.active_invoice == invoice1

    invoice0.expires_on = _fixed_now + timedelta(4)
    invoice0.save()
    assert invoice0.expires_on < invoice1.expires_on, "Sanity"
    assert challenge.active_invoice == invoice0


@pytest.mark.django_db
def test_active_invoice_takes_overall_balance_into_account():
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

    with pytest.raises(InsufficientBudgetError):
        challenge.active_invoice
