import json
import uuid
from contextlib import nullcontext
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone

from grandchallenge.algorithms.models import Job
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKind,
    InterfaceKindChoices,
    InterfaceSuperKindChoices,
)
from grandchallenge.components.schemas import INTERFACE_VALUE_SCHEMA
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.evaluation_tests.factories import EvaluationFactory
from tests.factories import ImageFactory


@pytest.mark.django_db
def test_update_started_adds_time():
    j = AlgorithmJobFactory()
    assert j.started_at is None
    assert j.completed_at is None

    j.update_status(status=j.EXECUTING)

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
        (InterfaceKindChoices.ANY, False, False),
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
        (InterfaceKindChoices.THUMBNAIL_JPG, True, False),
        (InterfaceKindChoices.THUMBNAIL_PNG, True, False),
        (InterfaceKindChoices.SQREG, True, False),
        (InterfaceKindChoices.PDF, True, False),
        (InterfaceKindChoices.CHART, False, False),
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


def test_all_interfaces_in_schema():
    for i in InterfaceKind.interface_type_json():
        assert str(i) in INTERFACE_VALUE_SCHEMA["definitions"]


def test_all_interfaces_covered():
    assert {str(i) for i in InterfaceKindChoices} == {
        *InterfaceKind.interface_type_image(),
        *InterfaceKind.interface_type_file(),
        *InterfaceKind.interface_type_json(),
    }


@pytest.mark.django_db
def test_no_uuid_validation():
    # For multi job inputs we add uuid prefixes, so check that the relative
    # path does not contain a UUID
    i = ComponentInterfaceFactory(
        relative_path=f"{uuid.uuid4()}/whatever.json",
        kind=InterfaceKindChoices.ANY,
    )
    with pytest.raises(ValidationError) as e:
        i.full_clean()
    assert str(e.value) == "{'relative_path': ['Enter a valid value.']}"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind",
    (
        *InterfaceKind.interface_type_file(),
        *InterfaceKind.interface_type_json(),
    ),
)
def test_relative_path_file_ending(kind):
    if kind in InterfaceKind.interface_type_json():
        good_suffix = "json"
    else:
        good_suffix = kind.lower()

    i = ComponentInterfaceFactory(
        kind=kind,
        relative_path=f"foo/bar.{good_suffix}",
        store_in_database=kind in InterfaceKind.interface_type_json(),
    )
    i.full_clean()

    i.relative_path = "foo/bar"
    with pytest.raises(ValidationError):
        i.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind,image,file,value",
    (
        (InterfaceKindChoices.IMAGE, True, True, None),
        (InterfaceKindChoices.IMAGE, True, None, True),
        (InterfaceKindChoices.IMAGE, True, True, True),
        (InterfaceKindChoices.CSV, True, True, None),
        (InterfaceKindChoices.CSV, None, True, True),
        (InterfaceKindChoices.CSV, True, True, True),
        (InterfaceKindChoices.BOOL, True, None, True),
        (InterfaceKindChoices.BOOL, None, True, True),
        (InterfaceKindChoices.BOOL, True, True, True),
    ),
)
def test_multi_value_fails(kind, image, file, value):
    if image:
        image = ImageFactory()

    if file:
        file = ContentFile(json.dumps(True).encode("utf-8"), name="test.csv",)

    i = ComponentInterfaceFactory(kind=kind)
    v = ComponentInterfaceValue(
        interface=i, image=image, file=file, value=value
    )

    with pytest.raises(ValidationError):
        v.full_clean()


@pytest.mark.django_db
def test_valid_schema_ok():
    i = ComponentInterfaceFactory(
        schema={"type": "object"},
        relative_path="test.json",
        kind=InterfaceKindChoices.ANY,
    )
    i.full_clean()


@pytest.mark.django_db
def test_invalid_schema_raises_error():
    i = ComponentInterfaceFactory(schema={"type": "whatevs"})
    with pytest.raises(ValidationError) as e:
        i.full_clean()
    assert str(e.value).startswith(
        "{'schema': [\"Invalid schema: 'whatevs' is not valid under any of the given schemas"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("use_file", [True, False])
@pytest.mark.parametrize(
    "kind,value,expectation",
    (
        (InterfaceKindChoices.STRING, "hello", nullcontext()),
        (InterfaceKindChoices.STRING, "", nullcontext()),
        (InterfaceKindChoices.STRING, None, pytest.raises(ValidationError)),
        (InterfaceKindChoices.INTEGER, 42, nullcontext()),
        (InterfaceKindChoices.INTEGER, 42.1, pytest.raises(ValidationError)),
        (InterfaceKindChoices.FLOAT, 42, nullcontext()),
        (InterfaceKindChoices.FLOAT, "42", pytest.raises(ValidationError)),
        (InterfaceKindChoices.BOOL, True, nullcontext()),
        (InterfaceKindChoices.BOOL, "True", pytest.raises(ValidationError)),
        (
            InterfaceKindChoices.TWO_D_BOUNDING_BOX,
            {
                "version": {"major": 1, "minor": 0},
                "type": "2D bounding box",
                "name": "test_name",
                "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 0, 0]],
            },
            nullcontext(),
        ),
        (
            InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple 2D bounding boxes",
                "name": "test_name",
                "boxes": [
                    {
                        "corners": [
                            [0, 0, 0],
                            [10, 0, 0],
                            [10, 10, 0],
                            [0, 0, 0],
                        ]
                    }
                ],
            },
            nullcontext(),
        ),
        (
            InterfaceKindChoices.DISTANCE_MEASUREMENT,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Distance measurement",
                "name": "test",
                "start": [1, 2, 3],
                "end": [4, 5, 6],
            },
            nullcontext(),
        ),
        (
            InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple distance measurements",
                "name": "test",
                "lines": [
                    {"start": [1, 2, 3], "end": [4, 5, 6]},
                    {"start": [1, 2, 3], "end": [4, 5, 6]},
                ],
            },
            nullcontext(),
        ),
        (
            InterfaceKindChoices.POINT,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Point",
                "name": "test",
                "point": [1, 2, 3],
            },
            nullcontext(),
        ),
        (
            InterfaceKindChoices.MULTIPLE_POINTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple points",
                "name": "test",
                "points": [{"point": [1, 2, 3]}, {"point": [4, 5, 6]}],
            },
            nullcontext(),
        ),
        (
            InterfaceKindChoices.POLYGON,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Polygon",
                "name": "test",
                "seed_point": [1, 2, 3],
                "path_points": [[1, 2, 3], [4, 5, 6]],
                "sub_type": "poly",
                "groups": ["a", "b"],
            },
            nullcontext(),
        ),
        (
            InterfaceKindChoices.MULTIPLE_POLYGONS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple polygons",
                "name": "test",
                "polygons": [
                    {
                        "name": "test",
                        "seed_point": [1, 2, 3],
                        "path_points": [[1, 2, 3], [4, 5, 6]],
                        "sub_type": "poly",
                        "groups": ["a", "b"],
                    }
                ],
            },
            nullcontext(),
        ),
        (InterfaceKindChoices.CHOICE, "First", nullcontext()),
        (InterfaceKindChoices.CHOICE, 1, pytest.raises(ValidationError)),
        (InterfaceKindChoices.MULTIPLE_CHOICE, ["1", "2"], nullcontext()),
        (InterfaceKindChoices.MULTIPLE_CHOICE, [], nullcontext()),
        (
            InterfaceKindChoices.MULTIPLE_CHOICE,
            [1, 2],
            pytest.raises(ValidationError),
        ),
        (InterfaceKindChoices.ANY, [], nullcontext()),
        (InterfaceKindChoices.ANY, None, nullcontext()),
        (InterfaceKindChoices.ANY, {}, nullcontext()),
        (
            InterfaceKindChoices.CHART,
            {
                "description": "A simple bar chart with embedded data.",
                "data": {
                    "values": [
                        {"a": "A", "b": 28},
                        {"a": "B", "b": 55},
                        {"a": "C", "b": 43},
                        {"a": "D", "b": 91},
                        {"a": "E", "b": 81},
                        {"a": "F", "b": 53},
                        {"a": "G", "b": 19},
                        {"a": "H", "b": 87},
                        {"a": "I", "b": 52},
                    ]
                },
                "mark": "bar",
                "encoding": {
                    "x": {
                        "field": "a",
                        "type": "nominal",
                        "axis": {"labelAngle": 0},
                    },
                    "y": {"field": "b", "type": "quantitative"},
                },
            },
            nullcontext(),
        ),
        (
            InterfaceKindChoices.CHART,
            {
                "description": "A simple bar chart with embedded data.",
                "wrong-property-name": {
                    "values": [
                        {"a": "A", "b": 28},
                        {"a": "B", "b": 55},
                        {"a": "C", "b": 43},
                        {"a": "D", "b": 91},
                        {"a": "E", "b": 81},
                        {"a": "F", "b": 53},
                        {"a": "G", "b": 19},
                        {"a": "H", "b": 87},
                        {"a": "I", "b": 52},
                    ]
                },
                "mark": "bar",
                "encoding": {
                    "x": {
                        "field": "a",
                        "type": "nominal",
                        "axis": {"labelAngle": 0},
                    },
                    "y": {"field": "b", "type": "quantitative"},
                },
            },
            pytest.raises(ValidationError),
        ),
    ),
)
def test_default_validation(kind, value, expectation, use_file):
    i = ComponentInterfaceFactory(kind=kind, store_in_database=not use_file)

    if use_file:
        kwargs = {
            "file": ContentFile(
                json.dumps(value).encode("utf-8"), name="test.json",
            )
        }
    else:
        kwargs = {"value": value}

    v = ComponentInterfaceValue(interface=i, **kwargs)

    with expectation:
        v.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize("use_file", [True, False])
@pytest.mark.parametrize(
    "kind,value,invalidation_schema",
    (
        (
            InterfaceKindChoices.STRING,
            "hello",
            {"type": "string", "pattern": "^[A-Z]+$"},
        ),
        (InterfaceKindChoices.INTEGER, 42, {"type": "integer", "maximum": 40}),
        (
            InterfaceKindChoices.FLOAT,
            42.0,
            {"type": "number", "multipleOf": 10.1},
        ),
        (InterfaceKindChoices.BOOL, True, {"enum": [False]}),
        (
            InterfaceKindChoices.TWO_D_BOUNDING_BOX,
            {
                "version": {"major": 1, "minor": 0},
                "type": "2D bounding box",
                "name": "test_name",
                "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 0, 0]],
            },
            {"properties": {"name": {"pattern": "^[A-Z]+$"}}},
        ),
        (
            InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple 2D bounding boxes",
                "name": "test_name",
                "boxes": [
                    {
                        "corners": [
                            [0, 0, 0],
                            [10, 0, 0],
                            [10, 10, 0],
                            [0, 0, 0],
                        ]
                    }
                ],
            },
            {"properties": {"name": {"pattern": "^[A-Z]+$"}}},
        ),
        (
            InterfaceKindChoices.DISTANCE_MEASUREMENT,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Distance measurement",
                "name": "test",
                "start": [1, 2, 3],
                "end": [4, 5, 6],
            },
            {"properties": {"name": {"pattern": "^[A-Z]+$"}}},
        ),
        (
            InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple distance measurements",
                "name": "test",
                "lines": [
                    {"start": [1, 2, 3], "end": [4, 5, 6]},
                    {"start": [1, 2, 3], "end": [4, 5, 6]},
                ],
            },
            {"properties": {"name": {"pattern": "^[A-Z]+$"}}},
        ),
        (
            InterfaceKindChoices.POINT,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Point",
                "name": "test",
                "point": [1, 2, 3],
            },
            {"properties": {"name": {"pattern": "^[A-Z]+$"}}},
        ),
        (
            InterfaceKindChoices.MULTIPLE_POINTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple points",
                "name": "test",
                "points": [{"point": [1, 2, 3]}, {"point": [4, 5, 6]}],
            },
            {"properties": {"name": {"pattern": "^[A-Z]+$"}}},
        ),
        (
            InterfaceKindChoices.POLYGON,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Polygon",
                "name": "test",
                "seed_point": [1, 2, 3],
                "path_points": [[1, 2, 3], [4, 5, 6]],
                "sub_type": "poly",
                "groups": ["a", "b"],
            },
            {"properties": {"name": {"pattern": "^[A-Z]+$"}}},
        ),
        (
            InterfaceKindChoices.MULTIPLE_POLYGONS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple polygons",
                "name": "test",
                "polygons": [
                    {
                        "name": "test",
                        "seed_point": [1, 2, 3],
                        "path_points": [[1, 2, 3], [4, 5, 6]],
                        "sub_type": "poly",
                        "groups": ["a", "b"],
                    }
                ],
            },
            {"properties": {"name": {"pattern": "^[A-Z]+$"}}},
        ),
        (InterfaceKindChoices.CHOICE, "First", {"enum": ["first"]}),
        (
            InterfaceKindChoices.MULTIPLE_CHOICE,
            ["1", "2"],
            {"type": "array", "items": {"enum": [1, 2]}},
        ),
        (InterfaceKindChoices.ANY, [], {"type": "object"}),
    ),
)
def test_extra_schema_validation(kind, value, invalidation_schema, use_file):
    i = ComponentInterfaceFactory(kind=kind, store_in_database=not use_file)

    if use_file:
        kwargs = {
            "file": ContentFile(
                json.dumps(value).encode("utf-8"), name="test.json",
            )
        }
    else:
        kwargs = {"value": value}

    v = ComponentInterfaceValue(interface=i, **kwargs)
    v.full_clean()

    i.schema = invalidation_schema

    with pytest.raises(ValidationError):
        v.full_clean()
