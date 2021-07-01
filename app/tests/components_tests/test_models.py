from datetime import timedelta

import pytest
from django.utils import timezone

from grandchallenge.algorithms.models import Job
from grandchallenge.components.models import (
    ComponentInterface,
    InterfaceKindChoices,
    InterfaceSuperKindChoices,
)
from tests.algorithms_tests.factories import AlgorithmJobFactory
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


@pytest.mark.parametrize(
    "kind,object_store_required,is_image",
    (
        (InterfaceKindChoices.CSV, True, False),
        (InterfaceKindChoices.ZIP, True, False),
        (InterfaceKindChoices.JSON, False, False),
        (InterfaceKindChoices.IMAGE, True, True),
        (InterfaceKindChoices.HEAT_MAP, True, True),
        (InterfaceKindChoices.SEGMENTATION, True, True),
        (InterfaceKindChoices.STRING, False, False),
        (InterfaceKindChoices.INTEGER, False, False),
        (InterfaceKindChoices.FLOAT, False, False),
        (InterfaceKindChoices.BOOL, False, False),
        (InterfaceKindChoices.CHOICE, False, False),
        (InterfaceKindChoices.MULTIPLE_CHOICE, False, False),
        (InterfaceKindChoices.TWO_D_BOUNDING_BOX, False, False),
        (InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES, False, False),
        (InterfaceKindChoices.DISTANCE_MEASUREMENT, False, False),
        (InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS, False, False),
        (InterfaceKindChoices.POINT, False, False),
        (InterfaceKindChoices.MULTIPLE_POINTS, False, False),
        (InterfaceKindChoices.POLYGON, False, False),
        (InterfaceKindChoices.MULTIPLE_POLYGONS, False, False),
    ),
)
def test_save_in_object_store(kind, object_store_required, is_image):
    ci = ComponentInterface(kind=kind, store_in_database=True)

    if object_store_required:
        assert ci.save_in_object_store is True
        if is_image:
            assert ci.super_kind == InterfaceSuperKindChoices.IMAGE
        else:
            assert ci.super_kind == InterfaceSuperKindChoices.FILE
        ci.store_in_database = False
    else:
        assert ci.save_in_object_store is False
        assert is_image is False  # Shouldn't happen!
        assert ci.super_kind == InterfaceSuperKindChoices.VALUE
        ci.store_in_database = False

    assert ci.save_in_object_store is True
    if is_image:
        assert ci.super_kind == InterfaceSuperKindChoices.IMAGE
    else:
        assert ci.super_kind == InterfaceSuperKindChoices.FILE
