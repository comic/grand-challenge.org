import json
import uuid
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import call

import pytest
from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.core.files.base import ContentFile
from panimg.models import MAXIMUM_SEGMENTS_LENGTH

from grandchallenge.algorithms.models import AlgorithmImage, Job
from grandchallenge.cases.models import Image
from grandchallenge.components.models import (
    INTERFACE_KIND_JSON_EXAMPLES,
    CIVData,
    ComponentInterface,
    ComponentInterfaceExampleValue,
    ComponentInterfaceValue,
    ImportStatusChoices,
    InterfaceKindChoices,
    InterfaceKinds,
)
from grandchallenge.components.schemas import INTERFACE_VALUE_SCHEMA
from grandchallenge.components.tasks import (
    delete_container_image,
    remove_container_image_from_registry,
)
from grandchallenge.core.storage import (
    private_s3_storage,
    protected_s3_storage,
)
from grandchallenge.reader_studies.models import Question
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
)
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.cases_tests.factories import (
    DICOMImageSetFactory,
    ImageFactoryWithImageFileTiff,
)
from tests.components_tests.factories import (
    ComponentInterfaceExampleValueFactory,
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.factories import MethodFactory
from tests.factories import ImageFactory, UserFactory, WorkstationImageFactory
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.uploads_tests.factories import UserUploadFactory
from tests.utils import create_raw_upload_image_session


@pytest.mark.parametrize("kind", InterfaceKindChoices)
def test_clean_store_in_db_false(kind):
    ci = ComponentInterface(kind=kind, store_in_database=False)

    ci._clean_store_in_database()
    assert True  # no exception raised


INTERFACE_KIND_CHOICES_ALLOW_STORE_IN_DB = sorted(
    [
        (InterfaceKindChoices.STRING, nullcontext()),
        (InterfaceKindChoices.INTEGER, nullcontext()),
        (InterfaceKindChoices.FLOAT, nullcontext()),
        (InterfaceKindChoices.BOOL, nullcontext()),
        (InterfaceKindChoices.TWO_D_BOUNDING_BOX, nullcontext()),
        (InterfaceKindChoices.DISTANCE_MEASUREMENT, nullcontext()),
        (InterfaceKindChoices.POINT, nullcontext()),
        (InterfaceKindChoices.POLYGON, nullcontext()),
        (InterfaceKindChoices.CHOICE, nullcontext()),
        (InterfaceKindChoices.MULTIPLE_CHOICE, nullcontext()),
        (InterfaceKindChoices.ANY, nullcontext()),
        (InterfaceKindChoices.CHART, nullcontext()),
        (InterfaceKindChoices.LINE, nullcontext()),
        (InterfaceKindChoices.ANGLE, nullcontext()),
        (InterfaceKindChoices.ELLIPSE, nullcontext()),
        (InterfaceKindChoices.THREE_POINT_ANGLE, nullcontext()),
        (
            InterfaceKindChoices.AFFINE_TRANSFORM_REGISTRATION,
            nullcontext(),
        ),
        (
            InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES,
            pytest.raises(ValidationError),
        ),
        (
            InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS,
            pytest.raises(ValidationError),
        ),
        (
            InterfaceKindChoices.MULTIPLE_POINTS,
            pytest.raises(ValidationError),
        ),
        (
            InterfaceKindChoices.MULTIPLE_POLYGONS,
            pytest.raises(ValidationError),
        ),
        (
            InterfaceKindChoices.MULTIPLE_LINES,
            pytest.raises(ValidationError),
        ),
        (
            InterfaceKindChoices.MULTIPLE_ANGLES,
            pytest.raises(ValidationError),
        ),
        (
            InterfaceKindChoices.MULTIPLE_ELLIPSES,
            pytest.raises(ValidationError),
        ),
        (
            InterfaceKindChoices.MULTIPLE_THREE_POINT_ANGLES,
            pytest.raises(ValidationError),
        ),
    ]
    + [
        (choice, pytest.raises(ValidationError))
        for choice in InterfaceKinds.image
    ]
    + [
        (choice, pytest.raises(ValidationError))
        for choice in InterfaceKinds.file
    ]
)


def test_all_interface_kind_choices_covered_for_allow_store_in_db():
    assert {
        choice for choice, _ in INTERFACE_KIND_CHOICES_ALLOW_STORE_IN_DB
    } == set(InterfaceKindChoices)


@pytest.mark.parametrize(
    "kind, expectation",
    INTERFACE_KIND_CHOICES_ALLOW_STORE_IN_DB,
)
def test_clean_store_in_db_true(kind, expectation):
    ci = ComponentInterface(kind=kind, store_in_database=True)

    with expectation:
        ci._clean_store_in_database()


def test_all_interfaces_in_schema():
    for i in InterfaceKinds.json:
        assert str(i) in INTERFACE_VALUE_SCHEMA["definitions"]


def test_all_interfaces_covered():
    assert {str(i) for i in InterfaceKindChoices} == {
        *InterfaceKinds.image,
        *InterfaceKinds.file,
        *InterfaceKinds.json,
    }


@pytest.mark.parametrize(
    "kind,context",
    (
        *((k, nullcontext()) for k in sorted(InterfaceKinds.file)),
        *((k, nullcontext()) for k in sorted(InterfaceKinds.json)),
        (
            InterfaceKindChoices.PANIMG_IMAGE,
            pytest.raises(RuntimeError),
        ),
    ),
)
def test_all_file_type_covered(kind, context):
    ci = ComponentInterfaceFactory.build(kind=kind)

    with context:
        ci.allowed_file_types

    with context:
        ci.file_extension


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
    "kind, good_suffix",
    (
        (InterfaceKindChoices.CSV, "csv"),
        (InterfaceKindChoices.ZIP, "zip"),
        (InterfaceKindChoices.PDF, "pdf"),
        (InterfaceKindChoices.SQREG, "sqreg"),
        (InterfaceKindChoices.THUMBNAIL_JPG, "jpeg"),
        (InterfaceKindChoices.THUMBNAIL_PNG, "png"),
        (InterfaceKindChoices.OBJ, "obj"),
        (InterfaceKindChoices.MP4, "mp4"),
        (InterfaceKindChoices.NEWICK, "newick"),
        (InterfaceKindChoices.BIOM, "biom"),
        *((k, "json") for k in InterfaceKinds.json),
    ),
)
def test_relative_path_file_ending(kind, good_suffix):
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
        (InterfaceKindChoices.PANIMG_IMAGE, True, True, None),
        (InterfaceKindChoices.PANIMG_IMAGE, True, None, True),
        (InterfaceKindChoices.PANIMG_IMAGE, True, True, True),
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
        InterfaceKindChoices.PANIMG_IMAGE,
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
    if kind == InterfaceKindChoices.PANIMG_IMAGE:
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

    if kind == InterfaceKindChoices.PANIMG_IMAGE:
        image = ImageFactory()
        civ.image = image
    elif kind == InterfaceKindChoices.CSV:
        file = ContentFile(b"Foo2", name="test2.csv")
        civ.file = file
    elif kind == InterfaceKindChoices.BOOL:
        civ.value = False
    elif kind == InterfaceKindChoices.STRING:
        civ.value = "Foo"

    civ.full_clean()

    with pytest.raises(ValidationError):
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
        (
            InterfaceKindChoices.AFFINE_TRANSFORM_REGISTRATION,
            {
                "3d_affine_transform": [
                    [1, 2, 3, 4],
                    [5, 6, 7, 8],
                    [9, 10, 11, 12],
                    [13, 14, 15, 16],
                ],
            },
            nullcontext(),
        ),
        (
            InterfaceKindChoices.AFFINE_TRANSFORM_REGISTRATION,
            {
                "3d_affine_transform": [
                    [1, 2, 3],  # <- missing one number
                    [5, 6, 7, 8],
                    [9, 10, 11, 12],
                    [13, 14, 15, 16],
                ],
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
                "name": "ml.m7i.large",
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
        "title": "ml.m7i.large / 2 CPU / 8 GB Memory / No GPU",
        "data": {
            "values": [
                {
                    "Metric": "CPUUtilization",
                    "Timestamp": "2022-06-09T09:38:00+00:00",
                    "Percent": 0.00338942,
                },
                {
                    "Metric": "CPUUtilization",
                    "Timestamp": "2022-06-09T09:37:00+00:00",
                    "Percent": 0.000651835,
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
                    {"calculate": "100*datum.Percent", "as": "Percent100"}
                ],
                "encoding": {
                    "x": {
                        "timeUnit": "yearmonthdatehoursminutesseconds",
                        "field": "Timestamp",
                        "title": "Local Time",
                    },
                    "y": {
                        "field": "Percent100",
                        "type": "quantitative",
                        "title": "Utilization / %",
                        "scale": {"domain": [0, 100]},
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
                        "timeUnit": "yearmonthdatehoursminutesseconds",
                        "field": "Timestamp",
                        "title": "Local Time",
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
                "encoding": {"y": {"datum": 50.0}},
            },
            {
                "data": {"values": [{}]},
                "mark": {"type": "text", "baseline": "line-bottom"},
                "encoding": {
                    "text": {"datum": "Single CPU Thread"},
                    "y": {"datum": 50.0},
                },
            },
        ],
    }


@pytest.mark.django_db
def test_clean_overlay_segments_with_values():
    ci = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.PANIMG_SEGMENTATION,
        overlay_segments=[{"name": "s1", "visible": True, "voxel_value": 1}],
    )
    ci._clean_overlay_segments()

    ComponentInterfaceValueFactory(interface=ci)
    ci.overlay_segments = [
        {"name": "s2", "visible": True, "voxel_value": 1},
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

    ci = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.PANIMG_SEGMENTATION,
        relative_path="images/test",
        overlay_segments=[{"name": "s1", "visible": True, "voxel_value": 1}],
    )
    ci._clean_overlay_segments()

    question.interface = ci
    question.save()
    ci.overlay_segments = [
        {"name": "s2", "visible": True, "voxel_value": 1},
    ]
    with pytest.raises(ValidationError) as e:
        ci._clean_overlay_segments()
    assert e.value.message == (
        "Overlay segments cannot be changed, as values or questions for this "
        "ComponentInterface exist."
    )


@pytest.mark.django_db
def test_clean_overlay_segments():
    ci = ComponentInterface(kind=InterfaceKindChoices.STRING)
    ci.overlay_segments = [{"name": "s1", "visible": True, "voxel_value": 1}]
    with pytest.raises(ValidationError) as e:
        ci._clean_overlay_segments()
    assert (
        e.value.message
        == "Overlay segments should only be set for segmentations"
    )

    ci = ComponentInterface(kind=InterfaceKindChoices.PANIMG_SEGMENTATION)
    with pytest.raises(ValidationError) as e:
        ci._clean_overlay_segments()
    assert e.value.message == "Overlay segments must be set for this interface"

    ci.overlay_segments = [
        {"name": "s1", "visible": True, "voxel_value": 1},
        {"name": "s2", "visible": True, "voxel_value": 3},
    ]
    with pytest.raises(ValidationError) as e:
        ci._clean_overlay_segments()
    assert (
        e.value.message
        == "Voxel values for overlay segments must be contiguous."
    )

    ci.overlay_segments = [
        {"name": "s1", "visible": True, "voxel_value": 1},
        {"name": "s2", "visible": True, "voxel_value": 2},
    ]
    ci._clean_overlay_segments()


@pytest.mark.parametrize(
    "updated_segments, expectation",
    (
        [
            [{"name": "s1", "visible": True, "voxel_value": 1}],
            pytest.raises(ValidationError),
        ],  # deletes existing voxel values
        [
            [
                {"name": "sfoo", "visible": True, "voxel_value": 1},
                {"name": "s2", "visible": True, "voxel_value": 2},
            ],
            pytest.raises(ValidationError),
        ],  # changes name of existing voxel value
        [
            [
                {"name": "s1", "visible": True, "voxel_value": 1},
                {"name": "s2", "visible": True, "voxel_value": 2},
                {"name": "s3", "visible": True, "voxel_value": 3},
            ],
            nullcontext(),
        ],  # adds new voxel value
    ),
)
@pytest.mark.django_db
def test_overlay_segments_can_be_extended(updated_segments, expectation):
    ci = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.PANIMG_SEGMENTATION,
        overlay_segments=[
            {"name": "s1", "visible": True, "voxel_value": 1},
            {"name": "s2", "visible": True, "voxel_value": 2},
        ],
    )
    ComponentInterfaceValueFactory(interface=ci)

    ci.overlay_segments = updated_segments

    with expectation:
        ci._clean_overlay_segments()


@pytest.mark.django_db
def test_validate_voxel_values():
    ci = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.PANIMG_SEGMENTATION
    )
    im = ImageFactory(segments=None)
    assert ci._validate_voxel_values(im) is None

    ci.overlay_segments = [{"name": "s1", "visible": True, "voxel_value": 1}]
    ci.save()

    error_msg = (
        "Image segments could not be determined, ensure the voxel values "
        "are integers and that it contains no more than "
        f"{MAXIMUM_SEGMENTS_LENGTH} segments. Ensure the image has the "
        "minimum and maximum voxel values set as tags if the image is a TIFF "
        "file."
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

    im = ImageFactoryWithImageFileTiff()
    ci.overlay_segments = [
        {"name": "s1", "visible": True, "voxel_value": 1},
        {"name": "s2", "visible": True, "voxel_value": 2},
    ]
    with pytest.raises(ValidationError) as e:
        ci._validate_voxel_values(im)
    assert e.value.message == error_msg
    im = ImageFactoryWithImageFileTiff(segments=[1, 2, 3])
    ci.overlay_segments = [
        {"name": "s1", "visible": True, "voxel_value": 1},
        {"name": "s2", "visible": True, "voxel_value": 3},
    ]
    with pytest.raises(ValidationError) as e:
        ci._validate_voxel_values(im)
    assert e.value.message == (
        "The valid voxel values for this segmentation are: {0, 1, 3}. "
        "This segmentation is invalid as it contains the voxel values: {2}."
    )
    ci.overlay_segments = [
        {"name": "s1", "visible": True, "voxel_value": 1},
        {"name": "s2", "visible": True, "voxel_value": 2},
    ]
    with pytest.raises(ValidationError) as e:
        ci._validate_voxel_values(im)
    assert e.value.message == (
        "The valid voxel values for this segmentation are: {0, 1, 2}. "
        "This segmentation is invalid as it contains the voxel values: {3}."
    )
    im = ImageFactoryWithImageFileTiff(segments=[1, 2])
    assert ci._validate_voxel_values(im) is None


INTERFACE_KIND_CHOICES_DICOM_KIND = sorted(
    [
        (
            InterfaceKindChoices.DICOM_IMAGE_SET,
            True,
        )
    ]
    + [(choice, False) for choice in InterfaceKinds.panimg]
)


def test_all_image_kind_choices_covered_for_validate_image_kind():
    assert {
        choice for choice, _ in INTERFACE_KIND_CHOICES_DICOM_KIND
    } == InterfaceKinds.image


@pytest.mark.parametrize(
    "interface_kind, is_dicom_kind", INTERFACE_KIND_CHOICES_DICOM_KIND
)
@pytest.mark.django_db
def test_validate_image_kind_with_dicom_image(interface_kind, is_dicom_kind):
    dicom_image_set = DICOMImageSetFactory()
    dicom_image = ImageFactory(dicom_image_set=dicom_image_set)
    civ = ComponentInterfaceValueFactory(
        interface__kind=interface_kind, image=dicom_image
    )

    if is_dicom_kind:
        context = nullcontext()
    else:
        context = pytest.raises(ValidationError)

    with context:
        civ._validate_image_kind()


@pytest.mark.parametrize(
    "interface_kind, is_dicom_kind", INTERFACE_KIND_CHOICES_DICOM_KIND
)
@pytest.mark.django_db
def test_validate_image_kind_with_panimg_image(interface_kind, is_dicom_kind):
    panimg_image = ImageFactory()
    civ = ComponentInterfaceValueFactory(
        interface__kind=interface_kind, image=panimg_image
    )

    if is_dicom_kind:
        context = pytest.raises(ValidationError)
    else:
        context = nullcontext()

    with context:
        civ._validate_image_kind()


@pytest.mark.django_db
def test_can_execute():
    ai = AlgorithmImageFactory(image=None)

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
def test_can_execute_removed_image():
    ai = AlgorithmImageFactory(image=None)

    assert ai.can_execute is False
    assert ai not in AlgorithmImage.objects.executable_images()

    ai.is_manifest_valid = True
    ai.is_in_registry = True
    ai.is_removed = False
    ai.save()

    del ai.can_execute
    assert ai.can_execute is True
    assert ai in AlgorithmImage.objects.executable_images()

    ai.is_removed = True
    ai.save()

    del ai.can_execute
    assert ai.can_execute is False
    assert ai not in AlgorithmImage.objects.executable_images()


@pytest.mark.django_db
def test_no_job_without_image(django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks() as callbacks:
        ai = AlgorithmImageFactory(image=None)

    assert len(callbacks) == 0
    assert ai.import_status == ImportStatusChoices.INITIALIZED


@pytest.mark.django_db
def test_one_job_with_image(
    algorithm_io_image, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks() as callbacks:
        ai = AlgorithmImageFactory(image__from_path=algorithm_io_image)

    assert len(callbacks) == 1
    assert "grandchallenge.components.tasks.validate_docker_image" in str(
        callbacks[0]
    )
    assert ai.import_status == ImportStatusChoices.QUEUED


@pytest.mark.django_db
def test_can_change_from_empty(django_capture_on_commit_callbacks):
    ai = AlgorithmImageFactory(image=None)

    with django_capture_on_commit_callbacks() as callbacks:
        ai.image = ContentFile(b"Foo1", name="blah")
        ai.save()

    assert len(callbacks) == 1
    assert "grandchallenge.components.tasks.validate_docker_image" in str(
        callbacks[0]
    )
    assert ai.import_status == ImportStatusChoices.QUEUED


@pytest.mark.django_db
def test_cannot_change_image(algorithm_io_image):
    ai = AlgorithmImageFactory(image__from_path=algorithm_io_image)

    ai.image = ContentFile(b"Foo1", name="blah")

    with pytest.raises(RuntimeError) as error:
        ai.save()

    assert str(error.value) == "The image cannot be changed"


@pytest.mark.django_db
def test_cannot_add_image_when_removed(algorithm_io_image):
    ai = AlgorithmImageFactory(is_removed=True, image="")

    ai.image = ContentFile(b"Foo1", name="blah")

    with pytest.raises(RuntimeError) as error:
        ai.save()

    assert str(error.value) == "Image cannot be set when removed"


@pytest.mark.django_db
def test_remove_container_image_from_registry(
    algorithm_io_image,
    settings,
    django_capture_on_commit_callbacks,
    mocker,
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    mock_remove_tag_from_registry = mocker.patch(
        # remove_tag_from_registry is only implemented for ECR
        "grandchallenge.components.tasks.remove_tag_from_registry"
    )

    with django_capture_on_commit_callbacks(execute=True):
        ai = AlgorithmImageFactory(image__from_path=algorithm_io_image)

    ai.refresh_from_db()

    assert ai.can_execute is True
    assert ai.is_manifest_valid is True
    assert (
        ai.latest_shimmed_version == settings.COMPONENTS_SAGEMAKER_SHIM_VERSION
    )
    assert ai.is_in_registry is True
    assert ai.is_desired_version is True
    assert ai.is_removed is False
    assert ai.size_in_storage != 0
    assert ai.size_in_registry != 0

    old_shimmed_repo_tag = ai.shimmed_repo_tag

    with django_capture_on_commit_callbacks() as callbacks:
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
    assert ai.is_desired_version is False
    assert ai.is_removed is False
    assert ai.size_in_storage != 0
    assert ai.size_in_registry == 0

    assert mock_remove_tag_from_registry.call_count == 2

    expected_calls = [
        call(repo_tag=old_shimmed_repo_tag),
        call(repo_tag=ai.original_repo_tag),
    ]

    mock_remove_tag_from_registry.assert_has_calls(
        expected_calls, any_order=False
    )


@pytest.mark.django_db
def test_delete_container_image(
    algorithm_io_image,
    settings,
    django_capture_on_commit_callbacks,
    mocker,
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    mock_remove_tag_from_registry = mocker.patch(
        # remove_tag_from_registry is only implemented for ECR
        "grandchallenge.components.tasks.remove_tag_from_registry"
    )

    with django_capture_on_commit_callbacks(execute=True):
        ai = AlgorithmImageFactory(image__from_path=algorithm_io_image)

    ai.refresh_from_db()

    assert ai.can_execute is True
    assert ai.is_manifest_valid is True
    assert (
        ai.latest_shimmed_version == settings.COMPONENTS_SAGEMAKER_SHIM_VERSION
    )
    assert ai.is_in_registry is True
    assert ai.is_desired_version is True
    assert ai.image != ""
    assert ai.is_removed is False
    assert ai.size_in_storage != 0
    assert ai.size_in_registry != 0

    old_shimmed_repo_tag = ai.shimmed_repo_tag

    with django_capture_on_commit_callbacks() as callbacks:
        delete_container_image(
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
    assert ai.is_desired_version is False
    assert ai.image == ""
    assert ai.is_removed is True
    assert ai.size_in_storage == 0
    assert ai.size_in_registry == 0

    assert mock_remove_tag_from_registry.call_count == 2

    expected_calls = [
        call(repo_tag=old_shimmed_repo_tag),
        call(repo_tag=ai.original_repo_tag),
    ]

    mock_remove_tag_from_registry.assert_has_calls(
        expected_calls, any_order=False
    )


@pytest.mark.django_db
def test_mark_desired_version():
    alg = AlgorithmFactory()
    i1, i2, i3 = AlgorithmImageFactory.create_batch(
        3,
        algorithm=alg,
        is_manifest_valid=True,
        is_in_registry=True,
        image=None,
    )
    i3.is_desired_version = True
    i3.save()
    assert not any([i1.is_desired_version, i2.is_desired_version])

    i2.mark_desired_version()
    for image in [i1, i2, i3]:
        image.refresh_from_db()
    assert i2.is_desired_version
    assert not any([i1.is_desired_version, i3.is_desired_version])


@pytest.mark.parametrize(
    "base_object_factory, related_item_factory, base_object_lookup",
    (
        (ReaderStudyFactory, DisplaySetFactory, "reader_study"),
        (ArchiveFactory, ArchiveItemFactory, "archive"),
    ),
)
@pytest.mark.django_db
def test_linked_component_interfaces(
    base_object_factory, related_item_factory, base_object_lookup
):
    base_obj = base_object_factory()
    ob1, ob2 = related_item_factory.create_batch(
        2, **{base_object_lookup: base_obj}
    )
    ci1, ci2, ci3 = ComponentInterfaceFactory.create_batch(3)
    civ1a, _ = ComponentInterfaceValueFactory.create_batch(2, interface=ci1)
    civ2a, civ2b = ComponentInterfaceValueFactory.create_batch(
        2, interface=ci2
    )
    civ3 = ComponentInterfaceValueFactory(interface=ci3)

    ob1.values.add(civ1a, civ2a)
    ob2.values.add(civ1a, civ2b, civ3)

    assert set(base_obj.linked_component_interfaces) == {ci1, ci2, ci3}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "factory, expected_storage, download_context",
    (
        (
            MethodFactory,
            private_s3_storage,
            pytest.raises(NotImplementedError),
        ),
        (
            WorkstationImageFactory,
            private_s3_storage,
            pytest.raises(NotImplementedError),
        ),
        (AlgorithmImageFactory, protected_s3_storage, nullcontext()),
    ),
)
def test_correct_storage_set(factory, expected_storage, download_context):
    instance = factory()

    assert instance._meta.get_field("image").storage == expected_storage

    with download_context:
        _ = instance.image.url


@pytest.mark.parametrize(
    "image,succeeds",
    (
        ("simple_2d_displacement_field_valid.mha", True),
        ("simple_2d_displacement_field_invalid.mha", False),
    ),
)
@pytest.mark.django_db
def test_displacement_field_validation(
    image, succeeds, settings, django_capture_on_commit_callbacks
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    image_paths = [Path(__file__).parent.absolute() / "resources" / image]
    session, uploaded_images = create_raw_upload_image_session(
        image_paths=image_paths,
    )

    with django_capture_on_commit_callbacks(execute=True):
        session.process_images()

    session.refresh_from_db()

    assert session.status == session.SUCCESS
    assert not session.error_message

    image = Image.objects.filter(origin=session).get()

    ci = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.PANIMG_DISPLACEMENT_FIELD
    )
    civ = ComponentInterfaceValueFactory(interface=ci, image=image)

    if succeeds:
        civ.full_clean()

        expected_size = [3, 1, 6, 6]

        assert len(image.shape) == 4
        assert image.shape[0] == 3
        assert image.shape == expected_size
        assert image.color_space == Image.COLOR_SPACE_GRAY

        assert [
            e for e in reversed(image.sitk_image.GetSize())
        ] == expected_size
    else:
        with pytest.raises(ValidationError) as error:
            civ.full_clean()

        assert (
            str(error.value)
            == "{'__all__': [\"Deformation and displacement field's 4th dimension must be a 3-component vector.\"]}"
        )


@pytest.mark.parametrize(
    "example_value,context",
    (
        (
            1,
            pytest.raises(ValidationError),
        ),
        (
            10,
            nullcontext(),
        ),
    ),
)
@pytest.mark.django_db
def test_ci_example_value(example_value, context):
    ci = ComponentInterfaceExampleValueFactory(
        interface__kind=InterfaceKindChoices.INTEGER,
        interface__schema={"type": "number", "minimum": 2, "maximum": 20},
        value=example_value,
    )

    with context:
        ci.full_clean()


@pytest.mark.django_db
def test_ci_example_value_non_json_kind_fail():
    v = ComponentInterfaceExampleValueFactory(
        interface__kind=InterfaceKindChoices.PANIMG_IMAGE,
    )

    with pytest.raises(
        ValidationError,
        match=r"Example value can be set for interfaces of JSON kind only",
    ):
        v.full_clean()


@pytest.mark.django_db
def test_schema_must_be_valid_for_example_value():
    ci = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.INTEGER, relative_path="test.json"
    )
    ComponentInterfaceExampleValueFactory(
        interface=ci,
        value=1,
    )

    ci.schema = {"type": "number", "minimum": 2, "maximum": 20}

    with pytest.raises(
        ValidationError,
        match=r".*The example value for this interface is not valid:.*instance is less than the minimum of 2.*",
    ):
        ci.full_clean()


@pytest.mark.parametrize(
    "kind, example",
    [
        (
            kind,
            example,
        )
        for kind, example in INTERFACE_KIND_JSON_EXAMPLES.items()
    ],
)
@pytest.mark.django_db
def test_interface_kind_json_kind_examples(kind, example):
    interface = ComponentInterfaceFactory(
        kind=kind, store_in_database=False, relative_path="test.json"
    )

    example.interface = interface
    example.full_clean()
    example.save()

    interface.full_clean()

    assert isinstance(example, ComponentInterfaceExampleValue)


def test_all_examples_present():
    assert set(INTERFACE_KIND_JSON_EXAMPLES.keys()) == set(InterfaceKinds.json)


@pytest.mark.django_db
def test_component_interface_value_manager():
    ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)
    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(
        2, interface=ci, value="Foo"
    )

    with pytest.raises(MultipleObjectsReturned):
        ComponentInterfaceValue.objects.get_or_create(
            interface=ci, value="Foo"
        )

    civ, created = ComponentInterfaceValue.objects.get_first_or_create(
        interface=ci, value="Foo"
    )

    assert civ == civ1
    assert not created


@pytest.mark.parametrize(
    "mock_error, expected_error, msg",
    (
        # Ensure all resource errors are covered
        (
            MemoryError,
            ValidationError,
            "The file was too large",
        ),
        (
            TimeLimitExceeded,
            ValidationError,
            "The file was too large",
        ),
        (
            SoftTimeLimitExceeded,
            ValidationError,
            "The file was too large",
        ),
        (
            UnicodeDecodeError,
            ValidationError,
            "The file could not be decoded",
        ),
        # Other Exceptions are not a ValidationError
        (
            RuntimeError("Some secret"),
            RuntimeError,
            "Some secret",
        ),
    ),
)
def test_validate_user_upload_resource_error_handling(
    mock_error, msg, expected_error
):
    ci = ComponentInterfaceFactory.build(kind=InterfaceKindChoices.FLOAT)
    civ = ComponentInterfaceValueFactory.build(interface=ci)

    assert ci.is_json_kind  # sanity

    class MockUserUpload:
        is_completed = True

        @classmethod
        def read_object(cls, *_, **__):
            if mock_error is UnicodeDecodeError:
                # Requires some args
                raise mock_error("foo", b"", 0, 1, "bar")
            raise mock_error

    with pytest.raises(expected_error) as err:
        civ.validate_user_upload(user_upload=MockUserUpload)

    if msg:
        assert msg in str(err)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind,expected_kwargs",
    (
        # Ensure queue is not passed since setting to None would
        # have Celery use the Celery-scope default ("celerly")
        (
            InterfaceKindChoices.STRING,
            {},
        ),
        (
            InterfaceKindChoices.NEWICK,
            {"queue": "acks-late-2xlarge"},
        ),
        (
            InterfaceKindChoices.BIOM,
            {"queue": "acks-late-2xlarge"},
        ),
    ),
)
def test_component_interface_custom_queue(kind, expected_kwargs, mocker):

    ci = ComponentInterfaceFactory(
        kind=kind,
        store_in_database=False,
    )
    user = UserFactory()

    # Need an existing CIVSet, use archive here since it is slightly easier setup
    archive = ArchiveFactory()
    archive.add_editor(user)
    ai = ArchiveItemFactory.build(archive=None)

    mock_task = mocker.patch(
        "grandchallenge.components.tasks.add_file_to_object"
    )
    ai.validate_values_and_execute_linked_task(
        values=[
            CIVData(
                interface_slug=ci.slug,
                value=UserUploadFactory(creator=user),
            )
        ],
        user=user,
    )
    assert mock_task.signature.called_once()  # Sanity

    # Ignore the to-task keyword arguments
    del mock_task.signature.call_args.kwargs["kwargs"]

    assert mock_task.signature.call_args.kwargs == expected_kwargs


def test_inputs_json_reserved():
    ci = ComponentInterface(relative_path="inputs.json")

    with pytest.raises(ValidationError) as error:
        ci.full_clean()

    assert "'relative_path': ['This relative path is reserved']" in str(
        error.value
    )


@pytest.mark.django_db
def test_no_default_value_allowed_when_file_required():
    i = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY,
        relative_path="foo/bar.json",
        store_in_database=True,
        default_value="foobar",
    )
    i.full_clean()

    i.store_in_database = False

    with pytest.raises(ValidationError):
        i.full_clean()
