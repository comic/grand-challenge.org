from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from actstream.actions import is_following
from actstream.models import Action
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import ProtectedError
from django.utils.timezone import datetime, now, timedelta

from grandchallenge.challenges.models import (
    Challenge,
    ChallengeRequest,
    OnboardingTask,
)
from grandchallenge.discussion_forums.models import ForumTopicKindChoices
from grandchallenge.notifications.models import Notification
from tests.discussion_forums_tests.factories import ForumTopicFactory
from tests.factories import (
    ChallengeFactory,
    ChallengeRequestFactory,
    OnboardingTaskFactory,
    UserFactory,
)
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
                average_size_test_image_mb_for_tasks=[10],
                inference_time_average_minutes_for_tasks=[10],
                task_id_for_phases=[1],
                number_of_teams_for_phases=[3],
                number_of_submissions_per_team_for_phases=[10],
                number_of_test_images_for_phases=[100],
            ),
            709.07,
            6000,
        ),
        (
            dict(
                task_ids=[1],
                algorithm_maximum_settable_memory_gb_for_tasks=[32],
                algorithm_selectable_gpu_type_choices_for_tasks=[["", "T4"]],
                average_size_test_image_mb_for_tasks=[10],
                inference_time_average_minutes_for_tasks=[10],
                task_id_for_phases=[1],
                number_of_teams_for_phases=[10],
                number_of_submissions_per_team_for_phases=[10],
                number_of_test_images_for_phases=[100],
            ),
            2361.98,
            7500,
        ),
        (
            dict(
                task_ids=[1],
                algorithm_maximum_settable_memory_gb_for_tasks=[32],
                algorithm_selectable_gpu_type_choices_for_tasks=[
                    ["", "A10G", "T4"]
                ],
                average_size_test_image_mb_for_tasks=[10],
                inference_time_average_minutes_for_tasks=[10],
                task_id_for_phases=[1],
                number_of_teams_for_phases=[10],
                number_of_submissions_per_team_for_phases=[10],
                number_of_test_images_for_phases=[100],
            ),
            3555.5,
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
                average_size_test_image_mb_for_tasks=[10, 100],
                inference_time_average_minutes_for_tasks=[5, 10],
                task_id_for_phases=[1, 1, 2, 2],
                number_of_submissions_per_team_for_phases=[10, 1, 10, 1],
                number_of_teams_for_phases=[3, 3, 3, 3],
                number_of_test_images_for_phases=[3, 100, 3, 100],
            ),
            363.97,
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
        average_size_test_image_mb_for_tasks=[100],
        inference_time_average_minutes_for_tasks=[10],
        task_id_for_phases=[1, 1],
        number_of_teams_for_phases=[10, 10],
        number_of_submissions_per_team_for_phases=[100, 10],
        number_of_test_images_for_phases=[100, 500],
    )

    costs_for_phases = [
        {
            # "name": "Phase 1",
            "compute_time": timedelta(minutes=10) * 10 * 100 * 100,
            "compute_costs_euros": 19581.10,
            "data_storage_size_gb": 100 * 100 / 1024,
            "data_storage_costs_euros": 6.57,
            "compute_and_storage_costs_euros": 19587.67,
        },
        {
            # "name": "Phase 2",
            "compute_time": timedelta(minutes=10) * 10 * 10 * 500,
            "compute_costs_euros": 9790.55,
            "data_storage_size_gb": 500 * 100 / 1024,
            "data_storage_costs_euros": 32.82,
            "compute_and_storage_costs_euros": 9823.37,
        },
    ]
    for i_phase in range(2):
        for k, v in costs_for_phases[i_phase].items():
            assert (
                pytest.approx(
                    getattr(challenge_request, k + "_for_phases")[i_phase],
                    abs=0.01,
                )
                == v
            )
    assert challenge_request.total_docker_storage_size_gb == 6 * 10 * 100
    assert challenge_request.total_docker_storage_costs_euros == 4032.05
    assert (
        pytest.approx(
            challenge_request.total_compute_and_storage_costs_euros, abs=0.01
        )
        == 33443.09
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
        pytest.approx(challenge_request.total_compute_and_storage_costs_euros)
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
