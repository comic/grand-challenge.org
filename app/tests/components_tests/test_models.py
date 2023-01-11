import json
import uuid
from contextlib import nullcontext
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone
from django_capture_on_commit_callbacks import capture_on_commit_callbacks
from panimg.models import MAXIMUM_SEGMENTS_LENGTH

from grandchallenge.algorithms.models import AlgorithmImage, Job
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    ImportStatusChoices,
    InterfaceKind,
    InterfaceKindChoices,
    InterfaceSuperKindChoices,
)
from grandchallenge.components.schemas import INTERFACE_VALUE_SCHEMA
from grandchallenge.components.tasks import (
    remove_container_image_from_registry,
)
from grandchallenge.reader_studies.models import Question
from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.factories import EvaluationFactory
from tests.factories import ImageFactory
from tests.reader_studies_tests.factories import QuestionFactory


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
        # JSON types
        (InterfaceKindChoices.STRING, False, False),
        (InterfaceKindChoices.INTEGER, False, False),
        (InterfaceKindChoices.FLOAT, False, False),
        (InterfaceKindChoices.BOOL, False, False),
        (InterfaceKindChoices.TWO_D_BOUNDING_BOX, False, False),
        (InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES, False, False),
        (InterfaceKindChoices.DISTANCE_MEASUREMENT, False, False),
        (InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS, False, False),
        (InterfaceKindChoices.POINT, False, False),
        (InterfaceKindChoices.MULTIPLE_POINTS, False, False),
        (InterfaceKindChoices.POLYGON, False, False),
        (InterfaceKindChoices.MULTIPLE_POLYGONS, False, False),
        (InterfaceKindChoices.CHOICE, False, False),
        (InterfaceKindChoices.MULTIPLE_CHOICE, False, False),
        (InterfaceKindChoices.ANY, False, False),
        (InterfaceKindChoices.CHART, False, False),
        (InterfaceKindChoices.LINE, False, False),
        (InterfaceKindChoices.MULTIPLE_LINES, False, False),
        (InterfaceKindChoices.ANGLE, False, False),
        (InterfaceKindChoices.MULTIPLE_ANGLES, False, False),
        (InterfaceKindChoices.ELLIPSE, False, False),
        (InterfaceKindChoices.MULTIPLE_ELLIPSES, False, False),
        # Image types
        (InterfaceKindChoices.IMAGE, True, True),
        (InterfaceKindChoices.HEAT_MAP, True, True),
        (InterfaceKindChoices.SEGMENTATION, True, True),
        # File types
        (InterfaceKindChoices.CSV, True, False),
        (InterfaceKindChoices.ZIP, True, False),
        (InterfaceKindChoices.PDF, True, False),
        (InterfaceKindChoices.SQREG, True, False),
        (InterfaceKindChoices.THUMBNAIL_JPG, True, False),
        (InterfaceKindChoices.THUMBNAIL_PNG, True, False),
        (InterfaceKindChoices.OBJ, True, False),
        (InterfaceKindChoices.MP4, True, False),
    ),
)
def test_saved_in_object_store(kind, object_store_required, is_image):
    ci = ComponentInterface(kind=kind, store_in_database=True)

    if object_store_required:
        assert ci.saved_in_object_store is True
        if is_image:
            assert ci.super_kind == InterfaceSuperKindChoices.IMAGE
        else:
            assert ci.super_kind == InterfaceSuperKindChoices.FILE
        ci.store_in_database = False
    else:
        assert ci.saved_in_object_store is False
        assert is_image is False  # Shouldn't happen!
        assert ci.super_kind == InterfaceSuperKindChoices.VALUE
        ci.store_in_database = False

    assert ci.saved_in_object_store is True
    if is_image:
        assert ci.super_kind == InterfaceSuperKindChoices.IMAGE
    else:
        assert ci.super_kind == InterfaceSuperKindChoices.FILE


@pytest.mark.parametrize(
    "kind,object_store_required",
    (
        # JSON types
        (InterfaceKindChoices.STRING, False),
        (InterfaceKindChoices.INTEGER, False),
        (InterfaceKindChoices.FLOAT, False),
        (InterfaceKindChoices.BOOL, False),
        (InterfaceKindChoices.TWO_D_BOUNDING_BOX, False),
        (InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES, True),
        (InterfaceKindChoices.DISTANCE_MEASUREMENT, False),
        (InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS, True),
        (InterfaceKindChoices.POINT, False),
        (InterfaceKindChoices.MULTIPLE_POINTS, True),
        (InterfaceKindChoices.POLYGON, False),
        (InterfaceKindChoices.MULTIPLE_POLYGONS, True),
        (InterfaceKindChoices.CHOICE, False),
        (InterfaceKindChoices.MULTIPLE_CHOICE, False),
        (InterfaceKindChoices.ANY, False),
        (InterfaceKindChoices.CHART, False),
        (InterfaceKindChoices.LINE, False),
        (InterfaceKindChoices.MULTIPLE_LINES, True),
        (InterfaceKindChoices.ANGLE, False),
        (InterfaceKindChoices.MULTIPLE_ANGLES, True),
        (InterfaceKindChoices.ELLIPSE, False),
        (InterfaceKindChoices.MULTIPLE_ELLIPSES, True),
        # Image types
        (InterfaceKindChoices.IMAGE, True),
        (InterfaceKindChoices.HEAT_MAP, True),
        (InterfaceKindChoices.SEGMENTATION, True),
        # File types
        (InterfaceKindChoices.CSV, True),
        (InterfaceKindChoices.ZIP, True),
        (InterfaceKindChoices.PDF, True),
        (InterfaceKindChoices.SQREG, True),
        (InterfaceKindChoices.THUMBNAIL_JPG, True),
        (InterfaceKindChoices.THUMBNAIL_PNG, True),
    ),
)
def test_clean_store_in_db(kind, object_store_required):
    ci = ComponentInterface(kind=kind, store_in_database=False)
    ci._clean_store_in_database()
    assert ci.saved_in_object_store is True

    ci.store_in_database = True

    if object_store_required:
        with pytest.raises(ValidationError):
            ci._clean_store_in_database()
    else:
        ci._clean_store_in_database()
        assert ci.saved_in_object_store is False


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
        store_in_database=False,
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
        file = ContentFile(json.dumps(True).encode("utf-8"), name="test.csv")

    i = ComponentInterfaceFactory(kind=kind)
    v = ComponentInterfaceValue(
        interface=i, image=image, file=file, value=value
    )

    with pytest.raises(ValidationError):
        v.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind",
    (
        InterfaceKindChoices.IMAGE,
        InterfaceKindChoices.CSV,
        InterfaceKindChoices.BOOL,
        InterfaceKindChoices.STRING,
    ),
)
def test_civ_updating(kind):
    ci = ComponentInterfaceFactory(kind=kind)
    if kind == InterfaceKindChoices.STRING:
        ci.default_value = "Foo"
        ci.save()
    civ = ComponentInterfaceValueFactory(interface=ci)

    # updating from None or default value to a file, image, value works
    if kind == InterfaceKindChoices.IMAGE:
        image = ImageFactory()
        civ.image = image
        civ.full_clean()
        civ.save()
    elif kind == InterfaceKindChoices.CSV:
        file = ContentFile(b"Foo1", name="test.csv")
        civ.file = file
        civ.full_clean()
        civ.save()
    elif kind == InterfaceKindChoices.BOOL:
        civ.value = True
        civ.full_clean()
        civ.save()
    elif kind == InterfaceKindChoices.STRING:
        civ.value = "Bar"
        civ.full_clean()
        civ.save()

    civ = ComponentInterfaceValue.objects.last()

    # updating existing values does not work
    with pytest.raises(ValidationError):
        if kind == InterfaceKindChoices.IMAGE:
            image = ImageFactory()
            civ.image = image
            civ.full_clean()
            civ.save()
        elif kind == InterfaceKindChoices.CSV:
            file = ContentFile(b"Foo2", name="test2.csv")
            civ.file = file
            civ.full_clean()
            civ.save()
        elif kind == InterfaceKindChoices.BOOL:
            civ.value = False
            civ.full_clean()
            civ.save()
        elif kind == InterfaceKindChoices.STRING:
            civ.value = "Foo"
            civ.full_clean()
            civ.save()


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
        (
            InterfaceKindChoices.ANGLE,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Angle",
                "name": "test",
                "lines": [[[1, 2, 3], [4, 5, 6]], [[1, 2, 3], [4, 5, 6]]],
            },
            nullcontext(),
        ),
        (
            InterfaceKindChoices.MULTIPLE_ANGLES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple angles",
                "name": "test",
                "angles": [
                    {
                        "name": "test",
                        "lines": [
                            [[1, 2, 3], [4, 5, 6]],
                            [[1, 2, 3], [4, 5, 6]],
                        ],
                    }
                ],
            },
            nullcontext(),
        ),
        (
            InterfaceKindChoices.ELLIPSE,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Ellipse",
                "name": "test",
                "major_axis": [[1, 2, 3], [4, 5, 6]],
                "minor_axis": [[1, 2, 3], [4, 5, 6]],
            },
            nullcontext(),
        ),
        (
            InterfaceKindChoices.MULTIPLE_ELLIPSES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple ellipses",
                "name": "test",
                "ellipses": [
                    {
                        "name": "test",
                        "major_axis": [[1, 2, 3], [4, 5, 6]],
                        "minor_axis": [[1, 2, 3], [4, 5, 6]],
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
                json.dumps(value).encode("utf-8"), name="test.json"
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
        (
            InterfaceKindChoices.ANGLE,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Angle",
                "name": "test",
                "lines": [[[1, 2, 3], [4, 5, 6]], [[1, 2, 3], [4, 5, 6]]],
            },
            {"properties": {"name": {"pattern": "^[A-Z]+$"}}},
        ),
        (
            InterfaceKindChoices.MULTIPLE_ANGLES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple angles",
                "name": "test",
                "angles": [
                    {
                        "lines": [
                            [[1, 2, 3], [4, 5, 6]],
                            [[1, 2, 3], [4, 5, 6]],
                        ]
                    },
                    {
                        "lines": [
                            [[1, 2, 3], [4, 5, 6]],
                            [[1, 2, 3], [4, 5, 6]],
                        ]
                    },
                ],
            },
            {"properties": {"name": {"pattern": "^[A-Z]+$"}}},
        ),
        (
            InterfaceKindChoices.ELLIPSE,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Ellipse",
                "name": "test",
                "major_axis": [[0, 0, 0], [10, 1, 0.5]],
                "minor_axis": [[10, 0, 0], [10, 4, 0.5]],
                "probability": 0.9,
            },
            {"properties": {"name": {"pattern": "^[A-Z]+$"}}},
        ),
        (
            InterfaceKindChoices.MULTIPLE_ELLIPSES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple ellipses",
                "name": "test",
                "ellipses": [
                    {
                        "name": "First Ellipse",
                        "major_axis": [[0, 0, 0], [10, 1, 0.5]],
                        "minor_axis": [[10, 0, 0], [10, 4, 0.5]],
                    },
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
                json.dumps(value).encode("utf-8"), name="test.json"
            )
        }
    else:
        kwargs = {"value": value}

    v = ComponentInterfaceValue(interface=i, **kwargs)
    v.full_clean()

    i.schema = invalidation_schema

    with pytest.raises(ValidationError):
        v.full_clean()


def test_runtime_metrics_chart():
    job = Job(
        runtime_metrics={
            "instance": {
                "cpu": 2,
                "gpu_type": None,
                "gpus": 0,
                "memory": 8,
                "name": "ml.m5.large",
                "cents_per_hour": 13,
            },
            "metrics": [
                {
                    "label": "CPUUtilization",
                    "status": "Complete",
                    "timestamps": [
                        "2022-06-09T09:38:00+00:00",
                        "2022-06-09T09:37:00+00:00",
                    ],
                    "values": [0.677884, 0.130367],
                },
                {
                    "label": "MemoryUtilization",
                    "status": "Complete",
                    "timestamps": [
                        "2022-06-09T09:38:00+00:00",
                        "2022-06-09T09:37:00+00:00",
                    ],
                    "values": [1.14447, 0.875619],
                },
            ],
        }
    )

    assert job.runtime_metrics_chart == {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container",
        "padding": 0,
        "title": "ml.m5.large / 2 CPU / 8 GB Memory / No GPU",
        "data": {
            "values": [
                {
                    "Metric": "CPUUtilization",
                    "Timestamp": "2022-06-09T09:38:00+00:00",
                    "Percent": 0.00677884,
                },
                {
                    "Metric": "CPUUtilization",
                    "Timestamp": "2022-06-09T09:37:00+00:00",
                    "Percent": 0.00130367,
                },
                {
                    "Metric": "MemoryUtilization",
                    "Timestamp": "2022-06-09T09:38:00+00:00",
                    "Percent": 0.0114447,
                },
                {
                    "Metric": "MemoryUtilization",
                    "Timestamp": "2022-06-09T09:37:00+00:00",
                    "Percent": 0.00875619,
                },
            ]
        },
        "layer": [
            {
                "transform": [
                    {"calculate": "100*datum.Percent", "as": "Percent100"},
                ],
                "encoding": {
                    "x": {
                        "timeUnit": "hoursminutesseconds",
                        "field": "Timestamp",
                        "title": "Local Time / HH:MM:SS",
                    },
                    "y": {
                        "field": "Percent100",
                        "type": "quantitative",
                        "title": "Utilization / %",
                    },
                    "color": {"field": "Metric", "type": "nominal"},
                },
                "layer": [
                    {"mark": "line"},
                    {
                        "transform": [
                            {"filter": {"param": "hover", "empty": False}}
                        ],
                        "mark": "point",
                    },
                ],
            },
            {
                "transform": [
                    {
                        "pivot": "Metric",
                        "value": "Percent",
                        "groupby": ["Timestamp"],
                    }
                ],
                "mark": "rule",
                "encoding": {
                    "opacity": {
                        "condition": {
                            "value": 0.3,
                            "param": "hover",
                            "empty": False,
                        },
                        "value": 0,
                    },
                    "tooltip": [
                        {
                            "field": "CPUUtilization",
                            "type": "quantitative",
                            "format": ".2%",
                        },
                        {
                            "field": "MemoryUtilization",
                            "type": "quantitative",
                            "format": ".2%",
                        },
                    ],
                    "x": {
                        "timeUnit": "hoursminutesseconds",
                        "field": "Timestamp",
                        "title": "Local Time / HH:MM:SS",
                    },
                },
                "params": [
                    {
                        "name": "hover",
                        "select": {
                            "type": "point",
                            "fields": ["Timestamp"],
                            "nearest": True,
                            "on": "mouseover",
                            "clear": "mouseout",
                        },
                    }
                ],
            },
            {
                "data": {"values": [{}]},
                "mark": {"type": "rule", "strokeDash": [8, 8]},
                "encoding": {"y": {"datum": 200}},
            },
            {
                "data": {"values": [{}]},
                "mark": {"type": "text", "baseline": "line-bottom"},
                "encoding": {
                    "text": {"datum": "CPU Utilization Limit"},
                    "y": {"datum": 200},
                },
            },
            {
                "data": {"values": [{}]},
                "mark": {"type": "rule", "strokeDash": [8, 8]},
                "encoding": {"y": {"datum": 100}},
            },
            {
                "data": {"values": [{}]},
                "mark": {"type": "text", "baseline": "line-bottom"},
                "encoding": {
                    "text": {
                        "datum": "Memory / GPU / GPU Memory Utilization Limit"
                    },
                    "y": {"datum": 100},
                },
            },
        ],
    }


@pytest.mark.django_db
def test_clean_overlay_segments_with_values():
    ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.SEGMENTATION)
    ci.overlay_segments = [{"name": "s1", "visible": True, "voxel_value": 1}]
    ci._clean_overlay_segments()
    ci.save()

    ComponentInterfaceValueFactory(interface=ci)
    ci.overlay_segments = [
        {"name": "s1", "visible": True, "voxel_value": 1},
        {"name": "s2", "visible": True, "voxel_value": 2},
    ]
    with pytest.raises(ValidationError) as e:
        ci._clean_overlay_segments()
    assert e.value.message == (
        "Overlay segments cannot be changed, as values or questions for this "
        "ComponentInterface exist."
    )


@pytest.mark.django_db
def test_clean_overlay_segments_with_questions(reader_study_with_gt):
    question = QuestionFactory(
        reader_study=reader_study_with_gt,
        answer_type=Question.AnswerType.BOOL,
    )
    assert question.interface is None

    ci = ComponentInterface(
        kind=InterfaceKindChoices.SEGMENTATION, relative_path="images/test"
    )
    ci.overlay_segments = [{"name": "s1", "visible": True, "voxel_value": 1}]
    ci._clean_overlay_segments()
    ci.save()

    question.interface = ci
    question.save()
    ci.overlay_segments = [
        {"name": "s1", "visible": True, "voxel_value": 1},
        {"name": "s2", "visible": True, "voxel_value": 2},
    ]
    with pytest.raises(ValidationError) as e:
        ci._clean_overlay_segments()
    assert e.value.message == (
        "Overlay segments cannot be changed, as values or questions for this "
        "ComponentInterface exist."
    )


@pytest.mark.django_db
def test_validate_voxel_values():
    ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.SEGMENTATION)
    im = ImageFactory(segments=None)
    assert ci._validate_voxel_values(im) is None

    ci.overlay_segments = [{"name": "s1", "visible": True, "voxel_value": 1}]
    ci.save()

    error_msg = (
        "Image segments could not be determined, ensure the file is "
        "not a tiff file, its voxel values are integers and that it "
        f"contains no more than {MAXIMUM_SEGMENTS_LENGTH} segments."
    )
    im = ImageFactory(segments=None)
    with pytest.raises(ValidationError) as e:
        ci._validate_voxel_values(im)
    assert e.value.message == error_msg

    im = ImageFactory(segments=[0, 1, 2])
    with pytest.raises(ValidationError) as e:
        ci._validate_voxel_values(im)
    assert e.value.message == (
        "The valid voxel values for this segmentation are: {0, 1}. "
        "This segmentation is invalid as it contains the voxel values: {2}."
    )

    ci.overlay_segments = [
        {"name": "s1", "visible": True, "voxel_value": 1},
        {"name": "s2", "visible": True, "voxel_value": 2},
    ]
    ci.save()
    im = ImageFactory(segments=[0, 1, 2])
    assert ci._validate_voxel_values(im) is None


@pytest.mark.django_db
def test_can_execute():
    ai = AlgorithmImageFactory()

    assert ai.can_execute is False
    assert ai not in AlgorithmImage.objects.executable_images()

    ai.is_manifest_valid = True
    ai.is_in_registry = True
    ai.save()

    del ai.can_execute
    assert ai.can_execute is True
    assert ai in AlgorithmImage.objects.executable_images()

    ai.is_manifest_valid = False
    ai.is_in_registry = True
    ai.save()

    del ai.can_execute
    assert ai.can_execute is False
    assert ai not in AlgorithmImage.objects.executable_images()

    ai.is_manifest_valid = True
    ai.is_in_registry = False
    ai.save()

    del ai.can_execute
    assert ai.can_execute is False
    assert ai not in AlgorithmImage.objects.executable_images()


@pytest.mark.django_db
def test_can_execute_with_sagemaker(settings):
    settings.COMPONENTS_CREATE_SAGEMAKER_MODEL = False

    ai = AlgorithmImageFactory(
        is_manifest_valid=True, is_in_registry=True, is_on_sagemaker=False
    )

    assert ai.can_execute is True
    assert ai in AlgorithmImage.objects.executable_images()

    settings.COMPONENTS_CREATE_SAGEMAKER_MODEL = True

    del ai.can_execute
    assert ai.can_execute is False
    assert ai not in AlgorithmImage.objects.executable_images()

    ai.is_on_sagemaker = True
    ai.save()

    del ai.can_execute
    assert ai.can_execute is True
    assert ai in AlgorithmImage.objects.executable_images()


@pytest.mark.django_db
def test_no_job_without_image():
    with capture_on_commit_callbacks() as callbacks:
        ai = AlgorithmImageFactory(image=None)

    assert len(callbacks) == 0
    assert ai.import_status == ImportStatusChoices.INITIALIZED


@pytest.mark.django_db
def test_one_job_with_image(algorithm_image):
    with capture_on_commit_callbacks() as callbacks:
        ai = AlgorithmImageFactory(image__from_path=algorithm_image)

    assert len(callbacks) == 1
    assert "grandchallenge.components.tasks.validate_docker_image" in str(
        callbacks[0]
    )
    assert ai.import_status == ImportStatusChoices.QUEUED


@pytest.mark.django_db
def test_can_change_from_empty():
    ai = AlgorithmImageFactory(image=None)

    with capture_on_commit_callbacks() as callbacks:
        ai.image = "blah"
        ai.save()

    assert len(callbacks) == 1
    assert "grandchallenge.components.tasks.validate_docker_image" in str(
        callbacks[0]
    )
    assert ai.import_status == ImportStatusChoices.QUEUED


@pytest.mark.django_db
def test_cannot_change_image(algorithm_image):
    ai = AlgorithmImageFactory(image__from_path=algorithm_image)

    with pytest.raises(RuntimeError):
        ai.image = "blah"
        ai.save()


@pytest.mark.django_db
def test_remove_container_image_from_registry(algorithm_image, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    with capture_on_commit_callbacks(execute=True):
        ai = AlgorithmImageFactory(image__from_path=algorithm_image)

    ai.refresh_from_db()

    assert ai.can_execute is True
    assert ai.is_manifest_valid is True
    assert (
        ai.latest_shimmed_version == settings.COMPONENTS_SAGEMAKER_SHIM_VERSION
    )
    assert ai.is_in_registry is True

    with capture_on_commit_callbacks() as callbacks:
        remove_container_image_from_registry(
            pk=ai.pk,
            app_label=ai._meta.app_label,
            model_name=ai._meta.model_name,
        )

    assert len(callbacks) == 0

    ai.refresh_from_db()
    del ai.can_execute

    assert ai.can_execute is False
    assert ai.is_manifest_valid is True
    assert ai.latest_shimmed_version == ""
    assert ai.is_in_registry is False
    assert ai.is_on_sagemaker is False
