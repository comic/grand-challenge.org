from datetime import timedelta

import pytest
from django.utils import timezone

from grandchallenge.algorithms.models import Job
from grandchallenge.components.models import InterfaceKind
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.evaluation_tests.factories import EvaluationFactory


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
    _ = EvaluationFactory()

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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind,object_store_required",
    (
        (InterfaceKind.InterfaceKindChoices.CSV, True),
        (InterfaceKind.InterfaceKindChoices.ZIP, True),
        (InterfaceKind.InterfaceKindChoices.JSON, False),
        (InterfaceKind.InterfaceKindChoices.SEGMENTATION, True),
        (InterfaceKind.InterfaceKindChoices.IMAGE, True),
        (InterfaceKind.InterfaceKindChoices.HEAT_MAP, True),
        (InterfaceKind.InterfaceKindChoices.BOOL, False),
    ),
)
def test_save_in_object_store(kind, object_store_required):
    ci = ComponentInterfaceFactory(kind=kind, store_in_database=True)

    if object_store_required:
        assert ci.save_in_object_store is True
        ci.store_in_database = False
        assert ci.save_in_object_store is True
    else:
        assert ci.save_in_object_store is False
        ci.store_in_database = False
        assert ci.save_in_object_store is True
