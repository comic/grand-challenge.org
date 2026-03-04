from datetime import timedelta

import pytest
from celery import states
from django.utils import timezone

from grandchallenge.background_tasks.models import CeleryTaskDailyStats
from grandchallenge.background_tasks.tasks import aggregate_celery_daily_stats
from tests.background_tasks_tests.factories import TaskResultFactory


@pytest.fixture
def yesterday():
    return (timezone.now() - timedelta(days=1)).date()


@pytest.mark.django_db
def test_success_counts_and_durations(yesterday):
    now = timezone.now() - timedelta(days=1)
    TaskResultFactory(date_started=now, date_done=now + timedelta(seconds=10))
    TaskResultFactory(date_started=now, date_done=now + timedelta(seconds=20))
    TaskResultFactory(date_started=now, date_done=now + timedelta(seconds=30))
    TaskResultFactory(
        task_name="other",
        date_started=now,
        date_done=now + timedelta(seconds=30),
    )

    aggregate_celery_daily_stats()

    stats = CeleryTaskDailyStats.objects.get(
        date=yesterday, task_name="myapp.tasks.foo"
    )
    assert stats.success_count == 3
    assert stats.failure_count == 0
    assert stats.min_duration == timedelta(seconds=10)
    assert stats.max_duration == timedelta(seconds=30)
    assert stats.avg_duration == timedelta(seconds=20)


@pytest.mark.django_db
def test_failure_counts(yesterday):
    TaskResultFactory(
        status=states.FAILURE, date_started=yesterday, date_done=yesterday
    )
    TaskResultFactory(
        status=states.FAILURE, date_started=yesterday, date_done=yesterday
    )

    aggregate_celery_daily_stats()

    stats = CeleryTaskDailyStats.objects.get(
        date=yesterday, task_name="myapp.tasks.foo"
    )
    assert stats.failure_count == 2
    assert stats.success_count == 0
    assert stats.avg_duration is None


@pytest.mark.django_db
def test_mixed_statuses(yesterday):
    now = timezone.now() - timedelta(days=1)

    TaskResultFactory(
        status=states.SUCCESS,
        date_started=now,
        date_done=now + timedelta(seconds=10),
    )
    TaskResultFactory(
        status=states.FAILURE,
        date_started=now,
        date_done=now + timedelta(seconds=10),
    )

    aggregate_celery_daily_stats()

    stats = CeleryTaskDailyStats.objects.get(
        date=yesterday, task_name="myapp.tasks.foo"
    )
    assert stats.success_count == 1
    assert stats.failure_count == 1
    assert stats.avg_duration == timedelta(seconds=10)


@pytest.mark.django_db
def test_multiple_tasks(yesterday):
    TaskResultFactory(
        task_name="myapp.tasks.foo",
        date_started=yesterday,
        date_done=yesterday,
    )
    TaskResultFactory(
        task_name="myapp.tasks.bar",
        date_started=yesterday,
        date_done=yesterday,
    )
    TaskResultFactory(
        task_name="myapp.tasks.bar",
        status=states.FAILURE,
        date_started=yesterday,
        date_done=yesterday,
    )

    aggregate_celery_daily_stats()

    foo = CeleryTaskDailyStats.objects.get(
        date=yesterday, task_name="myapp.tasks.foo"
    )
    bar = CeleryTaskDailyStats.objects.get(
        date=yesterday, task_name="myapp.tasks.bar"
    )

    assert foo.success_count == 1
    assert bar.success_count == 1
    assert bar.failure_count == 1


@pytest.mark.django_db
def test_excludes_other_days():
    now = timezone.now()
    TaskResultFactory(
        date_started=now - timedelta(days=2, seconds=10),
        date_done=now - timedelta(days=2),
    )

    aggregate_celery_daily_stats()

    assert not CeleryTaskDailyStats.objects.filter(
        task_name="myapp.tasks.foo"
    ).exists()


@pytest.mark.django_db
def test_success_without_date_started_excluded_from_durations(yesterday):
    now = timezone.now() - timedelta(days=1)

    TaskResultFactory(date_started=now, date_done=now + timedelta(seconds=10))
    TaskResultFactory(date_started=None, date_done=now + timedelta(seconds=20))
    TaskResultFactory(date_started=now, date_done=None)
    TaskResultFactory(date_started=now)

    aggregate_celery_daily_stats()

    stats = CeleryTaskDailyStats.objects.get(
        date=yesterday, task_name="myapp.tasks.foo"
    )
    assert stats.success_count == 1
    assert stats.avg_duration == timedelta(seconds=10)


@pytest.mark.django_db
def test_idempotent(yesterday):
    TaskResultFactory(date_started=yesterday, date_done=yesterday)

    aggregate_celery_daily_stats()
    aggregate_celery_daily_stats()

    assert (
        CeleryTaskDailyStats.objects.filter(
            date=yesterday, task_name="myapp.tasks.foo"
        ).count()
        == 1
    )
