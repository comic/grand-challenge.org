from datetime import timedelta

import pytest
from django.utils import timezone

from grandchallenge.algorithms.models import Job
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.factories import JobFactory


@pytest.mark.django_db
def test_update_started_adds_time():
    j = AlgorithmJobFactory()
    assert j.started_at is None
    assert j.completed_at is None

    j.update_status(status=j.STARTED)

    j.refresh_from_db()
    assert j.started_at is not None
    assert j.completed_at is None

    j.update_status(status=j.SUCCESS)

    j.refresh_from_db()
    assert j.started_at is not None
    assert j.completed_at is not None


@pytest.mark.django_db
def test_duration():
    j = AlgorithmJobFactory()
    _ = JobFactory()

    jbs = Job.objects.with_duration()
    assert jbs[0].duration is None
    assert Job.objects.average_duration() is None

    now = timezone.now()
    j.started_at = now - timedelta(minutes=5)
    j.completed_at = now
    j.save()

    jbs = Job.objects.with_duration()
    assert jbs[0].duration == timedelta(minutes=5)
    assert Job.objects.average_duration() == timedelta(minutes=5)

    _ = AlgorithmJobFactory()
    assert Job.objects.average_duration() == timedelta(minutes=5)


@pytest.mark.django_db
def test_average_duration_filtering():
    completed_at = timezone.now()
    j1, _ = (
        AlgorithmJobFactory(
            completed_at=completed_at,
            started_at=completed_at - timedelta(minutes=5),
        ),
        AlgorithmJobFactory(
            completed_at=completed_at,
            started_at=completed_at - timedelta(minutes=10),
        ),
    )
    assert Job.objects.average_duration() == timedelta(minutes=7.5)
    assert Job.objects.filter(
        algorithm_image=j1.algorithm_image
    ).average_duration() == timedelta(minutes=5)
