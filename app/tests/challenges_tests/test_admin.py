from unittest.mock import MagicMock

import pytest
from django.utils.timezone import now, timedelta

from grandchallenge.challenges.admin import (
    mark_task_complete,
    move_task_deadline_1_week,
    move_task_deadline_4_weeks,
)
from grandchallenge.challenges.models import OnboardingTask
from tests.factories import ChallengeFactory, OnboardingTaskFactory


@pytest.mark.django_db
def test_onboarding_task_mark_complete_action():
    ch = ChallengeFactory()
    tasks = OnboardingTaskFactory.create_batch(3, challenge=ch)

    for task in tasks:  # Sanity
        assert not task.complete

    mark_task_complete(
        MagicMock(),
        None,
        OnboardingTask.objects.filter(pk__in=[tasks[0].pk, tasks[1].pk]),
    )

    for task in tasks:
        task.refresh_from_db()

    assert tasks[0].complete
    assert tasks[1].complete
    assert not tasks[2].complete  # Sanity


@pytest.mark.django_db
def test_onboarding_task_move_dealine_action():
    ch = ChallengeFactory()
    deadline = now()
    tasks = OnboardingTaskFactory.create_batch(
        3, challenge=ch, deadline=deadline
    )

    move_task_deadline_1_week(
        MagicMock(),
        None,
        OnboardingTask.objects.filter(pk=tasks[0].pk),
    )
    move_task_deadline_4_weeks(
        MagicMock(),
        None,
        OnboardingTask.objects.filter(pk=tasks[1].pk),
    )

    for task in tasks:
        task.refresh_from_db()

    assert tasks[0].deadline - deadline == timedelta(weeks=1)
    assert tasks[1].deadline - deadline == timedelta(weeks=4)
    assert tasks[2].deadline == deadline  # Sanity
