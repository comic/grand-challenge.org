import pytest

from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.components.models import InterfaceKind
from grandchallenge.components.serializers import (
    ComponentInterfaceValuePostSerializer,
)
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.factories import ImageFactory, UploadSessionFactory, UserFactory

TEST_DATA = {
    "STR": "test",
    "INT": 12345,
    "BOOL": True,
    "FLT": 1.2,
    "2DBB": {
        "version": {"major": 1, "minor": 0},
        "type": "2D bounding box",
        "name": "test_name",
        "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]],
        "probability": 0.2,
    },
    "M2DB": {
        "type": "Multiple 2D bounding boxes",
        "boxes": [
            {
                "name": "foo",
                "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]],
            },
            {
                "corners": [[0, 0, 0], [10, 0, 0], [10, 20, 0], [0, 20, 0]],
                "probability": 0.2,
            },
        ],
        "version": {"major": 1, "minor": 0},
    },
    "DIST": {
        "version": {"major": 1, "minor": 0},
        "type": "Distance measurement",
        "name": "test_name",
        "start": [0, 0, 0],
        "end": [10, 0, 0],
        "probability": 1.0,
    },
    "MDIS": {
        "version": {"major": 1, "minor": 0},
        "type": "Multiple distance measurements",
        "name": "test_name",
        "lines": [
            {"name": "segment1", "start": [0, 0, 0], "end": [10, 0, 0]},
            {"start": [0, 0, 0], "end": [10, 0, 0], "probability": 0.5},
        ],
    },
    "POIN": {
        "version": {"major": 1, "minor": 0},
        "type": "Point",
        "name": "test_name",
        "point": [0, 0, 0],
        "probability": 0.41,
    },
    "MPOI": {
        "version": {"major": 1, "minor": 0},
        "type": "Multiple points",
        "name": "test_name",
        "points": [
            {"point": [0, 0, 0]},
            {"point": [0, 0, 0], "probability": 0.2},
        ],
    },
    "POLY": {
        "version": {"major": 1, "minor": 0},
        "type": "Polygon",
        "name": "test_name",
        "seed_point": [0, 0, 0],
        "path_points": [[0, 0, 0], [0, 0, 0]],
        "sub_type": "poly",
        "groups": ["a", "b"],
        "probability": 0.3,
    },
    "MPOL": {
        "version": {"major": 1, "minor": 0},
        "type": "Multiple polygons",
        "name": "test_name",
        "polygons": [
            {
                "name": "test_name",
                "seed_point": [0, 0, 0],
                "path_points": [[0, 0, 0], [0, 0, 0]],
                "sub_type": "poly",
                "groups": ["a", "b"],
            },
            {
                "name": "test_name",
                "seed_point": [0, 0, 0],
                "path_points": [[0, 0, 0], [0, 0, 0]],
                "sub_type": "poly",
                "groups": ["a", "b"],
                "probability": 0.54,
            },
        ],
    },
}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "civ, error_message",
    (
        (
            (
                {"interface": "interface-does-not-exist", "value": "dummy"},
                "Object with slug=interface-does-not-exist does not exist.",
            ),
        )
    ),
)
def test_civ_post_objects_do_not_exist(civ, error_message):
    # test
    serializer = ComponentInterfaceValuePostSerializer(data=civ)

    # verify
    assert not serializer.is_valid()
    assert error_message in str(serializer.errors)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind,",
    (
        InterfaceKind.InterfaceKindChoices.STRING,
        InterfaceKind.InterfaceKindChoices.INTEGER,
        InterfaceKind.InterfaceKindChoices.FLOAT,
        InterfaceKind.InterfaceKindChoices.BOOL,
        InterfaceKind.InterfaceKindChoices.TWO_D_BOUNDING_BOX,
        InterfaceKind.InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES,
        InterfaceKind.InterfaceKindChoices.DISTANCE_MEASUREMENT,
        InterfaceKind.InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS,
        InterfaceKind.InterfaceKindChoices.POINT,
        InterfaceKind.InterfaceKindChoices.MULTIPLE_POINTS,
        InterfaceKind.InterfaceKindChoices.POLYGON,
        InterfaceKind.InterfaceKindChoices.MULTIPLE_POLYGONS,
    ),
)
def test_civ_post_value_validation(kind):
    # setup
    interface = ComponentInterfaceFactory(kind=kind)

    for test in TEST_DATA:
        civ = {"interface": interface.slug, "value": TEST_DATA[test]}

        # test
        serializer = ComponentInterfaceValuePostSerializer(data=civ)

        # verify
        assert serializer.is_valid() == (
            kind == test
            or (
                # Ints are valid for float types
                kind == "FLT"
                and test == "INT"
            )
        )
        if not serializer.is_valid():
            assert "JSON does not fulfill schema: " in str(
                serializer.errors["__all__"][0]
            )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind",
    (
        InterfaceKind.InterfaceKindChoices.TWO_D_BOUNDING_BOX,
        InterfaceKind.InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES,
        InterfaceKind.InterfaceKindChoices.DISTANCE_MEASUREMENT,
        InterfaceKind.InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS,
        InterfaceKind.InterfaceKindChoices.POINT,
        InterfaceKind.InterfaceKindChoices.MULTIPLE_POINTS,
        InterfaceKind.InterfaceKindChoices.POLYGON,
        InterfaceKind.InterfaceKindChoices.MULTIPLE_POLYGONS,
        InterfaceKind.InterfaceKindChoices.STRING,
        InterfaceKind.InterfaceKindChoices.INTEGER,
        InterfaceKind.InterfaceKindChoices.FLOAT,
        InterfaceKind.InterfaceKindChoices.BOOL,
        InterfaceKind.InterfaceKindChoices.CHOICE,
        InterfaceKind.InterfaceKindChoices.MULTIPLE_CHOICE,
        # Do not test ANY type here as that is always valid
    ),
)
def test_civ_post_value_required(kind):
    # setup
    interface = ComponentInterfaceFactory(kind=kind)

    civ = {"interface": interface.slug}

    # test
    serializer = ComponentInterfaceValuePostSerializer(data=civ)

    # verify
    assert not serializer.is_valid()
    assert "JSON does not fulfill schema: None is not of type" in str(
        serializer.errors["__all__"][0]
    )


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", (InterfaceKind.interface_type_image()))
def test_civ_post_image_or_upload_required_validation(kind):
    # setup
    interface = ComponentInterfaceFactory(kind=kind)

    civ = {"interface": interface.slug}

    # test
    serializer = ComponentInterfaceValuePostSerializer(data=civ)

    # verify
    assert not serializer.is_valid()
    assert (
        f"upload_session or image are required for interface kind {kind}"
        in serializer.errors["non_field_errors"]
    )


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", (InterfaceKind.interface_type_image()))
def test_civ_post_image_permission_validation(kind, rf):
    # setup
    user = UserFactory()
    image = ImageFactory()
    interface = ComponentInterfaceFactory(kind=kind)

    civ = {"interface": interface.slug, "image": image.api_url}

    # test
    request = rf.get("/foo")
    request.user = user
    serializer = ComponentInterfaceValuePostSerializer(
        data=civ, context={"request": request}
    )

    # verify
    assert not serializer.is_valid()
    assert (
        "Invalid hyperlink - Object does not exist"
        in serializer.errors["image"][0]
    )


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", (InterfaceKind.interface_type_image()))
def test_civ_post_upload_permission_validation(kind, rf):
    # setup
    user = UserFactory()
    upload = UploadSessionFactory()
    interface = ComponentInterfaceFactory(kind=kind)

    civ = {"interface": interface.slug, "upload_session": upload.api_url}

    # test
    request = rf.get("/foo")
    request.user = user
    serializer = ComponentInterfaceValuePostSerializer(
        data=civ, context={"request": request}
    )

    # verify
    assert not serializer.is_valid()
    assert (
        "Invalid hyperlink - Object does not exist"
        in serializer.errors["upload_session"][0]
    )


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", (InterfaceKind.interface_type_image()))
def test_civ_post_image_not_ready_validation(kind, rf):
    # setup
    user = UserFactory()
    upload = UploadSessionFactory(
        status=RawImageUploadSession.REQUEUED, creator=user
    )
    interface = ComponentInterfaceFactory(kind=kind)

    civ = {"interface": interface.slug, "upload_session": upload.api_url}

    # test
    request = rf.get("/foo")
    request.user = user
    serializer = ComponentInterfaceValuePostSerializer(
        data=civ, context={"request": request}
    )

    # verify
    assert not serializer.is_valid()
    assert (
        "Invalid hyperlink - Object does not exist"
        in serializer.errors["upload_session"][0]
    )


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", (InterfaceKind.interface_type_image()))
def test_civ_post_image_valid(kind, rf):
    # setup
    user = UserFactory()
    upload = UploadSessionFactory(
        status=RawImageUploadSession.PENDING, creator=user
    )
    interface = ComponentInterfaceFactory(kind=kind)

    civ = {"interface": interface.slug, "upload_session": upload.api_url}

    # test
    request = rf.get("/foo")
    request.user = user
    serializer = ComponentInterfaceValuePostSerializer(
        data=civ, context={"request": request}
    )

    # verify
    assert serializer.is_valid()
