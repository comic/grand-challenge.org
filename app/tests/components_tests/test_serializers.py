import pytest
from guardian.shortcuts import assign_perm

from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.components.models import (
    ComponentInterfaceValue,
    InterfaceKindChoices,
    InterfaceKinds,
)
from grandchallenge.components.serializers import (
    ComponentInterfaceValuePostSerializer,
    ComponentInterfaceValueSerializer,
)
from tests.cases_tests.factories import DICOMImageSetFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UploadSessionFactory, UserFactory
from tests.uploads_tests.factories import UserUploadFactory

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
    "LINE": {
        "version": {"major": 1, "minor": 0},
        "type": "Line",
        "name": "test_name",
        "seed_points": [[0, 0, 0], [0, 0, 0]],
        "path_point_lists": [
            [[0, 0, 0], [0, 0, 0]],
            [[1, 1, 1], [1, 1, 1]],
        ],
        "probability": 0.3,
    },
    "MLIN": {
        "version": {"major": 1, "minor": 0},
        "type": "Multiple lines",
        "name": "test_name",
        "lines": [
            {
                "name": "test_name",
                "seed_points": [[0, 0, 0], [0, 0, 0]],
                "path_point_lists": [
                    [[0, 0, 0], [0, 0, 0]],
                    [[1, 1, 1], [1, 1, 1]],
                ],
                "probability": 0.54,
            },
            {
                "name": "test_name",
                "seed_points": [[0, 0, 0], [0, 0, 0]],
                "path_point_lists": [
                    [[0, 0, 0], [0, 0, 0]],
                    [[1, 1, 1], [1, 1, 1]],
                ],
                "probability": 0.54,
            },
        ],
    },
    "ANGL": {
        "version": {"major": 1, "minor": 0},
        "type": "Angle",
        "name": "test_name",
        "lines": [
            [[0, 0, 0], [0, 0, 0]],
            [[1, 1, 1], [1, 1, 1]],
        ],
        "probability": 0.3,
    },
    "MANG": {
        "version": {"major": 1, "minor": 0},
        "type": "Multiple angles",
        "name": "test_name",
        "angles": [
            {
                "name": "test_name",
                "lines": [
                    [[0, 0, 0], [0, 0, 0]],
                    [[1, 1, 1], [1, 1, 1]],
                ],
                "probability": 0.54,
            },
            {
                "name": "test_name",
                "lines": [
                    [[0, 0, 0], [0, 0, 0]],
                    [[1, 1, 1], [1, 1, 1]],
                ],
                "probability": 0.54,
            },
        ],
    },
    "ELLI": {
        "version": {"major": 1, "minor": 0},
        "type": "Ellipse",
        "name": "test_name",
        "major_axis": [[0, 0, 0], [0, 0, 0]],
        "minor_axis": [[1, 1, 1], [1, 1, 1]],
        "probability": 0.3,
    },
    "MELL": {
        "version": {"major": 1, "minor": 0},
        "type": "Multiple ellipses",
        "name": "test_name",
        "ellipses": [
            {
                "name": "test_name",
                "major_axis": [[0, 0, 0], [0, 0, 0]],
                "minor_axis": [[1, 1, 1], [1, 1, 1]],
                "probability": 0.54,
            },
            {
                "name": "test_name",
                "major_axis": [[0, 0, 0], [0, 0, 0]],
                "minor_axis": [[1, 1, 1], [1, 1, 1]],
                "probability": 0.54,
            },
        ],
    },
    "3ANG": {
        "version": {"major": 1, "minor": 0},
        "name": "Some annotation",
        "type": "Three-point angle",
        "angle": [
            [78.29, -17.14, 76.82],
            [76.801, -57.62, 84.43],
            [77.10, -18.97, 115.48],
        ],
        "probability": 0.92,
    },
    "M3AN": {
        "version": {"major": 1, "minor": 0},
        "name": "Some annotations",
        "type": "Multiple three-point angles",
        "angles": [
            {
                "name": "Annotation 1",
                "type": "Three-point angle",
                "angle": [
                    [78.29, -17.14, 76.82],
                    [76.801, -57.62, 84.43],
                    [77.10, -18.97, 115.48],
                ],
                "probability": 0.92,
            },
            {
                "name": "Annotation 2",
                "type": "Three-point angle",
                "angle": [
                    [78.29, -17.14, 76.82],
                    [76.801, -57.62, 84.43],
                    [77.10, -18.97, 115.48],
                ],
                "probability": 0.92,
            },
        ],
    },
}


@pytest.mark.django_db
def test_civ_post_objects_do_not_exist():
    payload = {
        "interface": "interface-does-not-exist",
        "value": "dummy",
    }
    error_message = "Object with slug=interface-does-not-exist does not exist."

    # test
    serializer = ComponentInterfaceValuePostSerializer(data=payload)

    # verify
    assert not serializer.is_valid()
    assert error_message in str(serializer.errors)


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", InterfaceKinds.json)
def test_civ_post_value_validation(kind):
    # setup
    interface = ComponentInterfaceFactory(kind=kind)

    for test in TEST_DATA:
        payload = {
            "interface": interface.slug,
            "value": TEST_DATA[test],
        }

        # test
        serializer = ComponentInterfaceValuePostSerializer(data=payload)

        # verify
        assert serializer.is_valid() == (
            kind == test
            or (
                # Ints are valid for float types
                kind == "FLT"
                and test == "INT"
            )
            or (
                # Strings are valid for multiple choice types
                kind == "CHOI"
                and test == "STR"
            )
            or (
                # All test data are valid for json type
                kind
                == "JSON"
            )
        )
        if not serializer.is_valid():
            assert "JSON does not fulfill schema: " in str(
                serializer.errors["__all__"][0]
            )


@pytest.mark.django_db
@pytest.mark.parametrize("kind", InterfaceKinds.json)
@pytest.mark.parametrize(
    "store_in_database, expected_error",
    (
        (True, "value is required for interface kind {kind}"),
        (False, "user_upload or file is required for interface kind {kind}"),
    ),
)
def test_civ_post_value_or_user_upload_required_validation(
    kind, store_in_database, expected_error
):
    # setup
    interface = ComponentInterfaceFactory(
        kind=kind,
        store_in_database=store_in_database,
    )

    payload = {"interface": interface.slug}

    # test
    serializer = ComponentInterfaceValuePostSerializer(data=payload)

    # verify
    assert not serializer.is_valid()
    assert (
        expected_error.format(kind=kind)
        in serializer.errors["non_field_errors"]
    )


@pytest.mark.django_db
@pytest.mark.parametrize("kind", InterfaceKinds.json)
def test_civ_post_user_upload_permission_validation(kind, rf):
    user = UserFactory()
    interface = ComponentInterfaceFactory(
        kind=kind,
        store_in_database=False,
    )
    upload = UserUploadFactory()
    payload = {
        "interface": interface.slug,
        "user_upload": upload.api_url,
    }
    request = rf.get("/foo")
    request.user = user

    serializer = ComponentInterfaceValuePostSerializer(
        data=payload, context={"request": request}
    )

    assert not serializer.is_valid()
    assert (
        "Invalid hyperlink - Object does not exist"
        in serializer.errors["user_upload"][0]
    )


@pytest.mark.django_db
@pytest.mark.parametrize("kind", InterfaceKinds.json)
def test_civ_post_user_upload_valid(kind, rf):
    user = UserFactory()
    interface = ComponentInterfaceFactory(
        kind=kind,
        store_in_database=False,
    )
    upload = UserUploadFactory(creator=user)
    payload = {
        "interface": interface.slug,
        "user_upload": upload.api_url,
    }
    request = rf.get("/foo")
    request.user = user

    serializer = ComponentInterfaceValuePostSerializer(
        data=payload, context={"request": request}
    )

    # verify
    assert serializer.is_valid()


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", InterfaceKinds.panimg)
def test_civ_post_image_or_upload_required_validation(kind):
    # setup
    interface = ComponentInterfaceFactory(kind=kind)

    payload = {"interface": interface.slug}

    # test
    serializer = ComponentInterfaceValuePostSerializer(data=payload)

    # verify
    assert not serializer.is_valid()
    assert (
        f"upload_session or image are required for interface kind {kind}"
        in serializer.errors["non_field_errors"]
    )


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", InterfaceKinds.dicom)
def test_civ_post_dicom_image_or_upload_required_validation(kind, rf):
    interface = ComponentInterfaceFactory(kind=kind)
    payload = {"interface": interface.slug}

    serializer = ComponentInterfaceValuePostSerializer(data=payload)

    assert not serializer.is_valid()
    assert (
        f"either user_uploads with image_name, or image are required for interface kind {kind}"
        in serializer.errors["non_field_errors"]
    )

    payload = {"interface": interface.slug, "image_name": "foobar"}

    serializer = ComponentInterfaceValuePostSerializer(data=payload)

    assert not serializer.is_valid()
    assert (
        f"either user_uploads with image_name, or image are required for interface kind {kind}"
        in serializer.errors["non_field_errors"]
    )

    user = UserFactory()
    upload = UserUploadFactory(creator=user)
    payload = {"interface": interface.slug, "user_uploads": [upload.api_url]}
    request = rf.get("/foo")
    request.user = user

    serializer = ComponentInterfaceValuePostSerializer(
        data=payload, context={"request": request}
    )

    assert not serializer.is_valid()
    assert (
        f"either user_uploads with image_name, or image are required for interface kind {kind}"
        in serializer.errors["non_field_errors"]
    )


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", InterfaceKinds.image)
def test_civ_post_image_permission_validation(kind, rf):
    # setup
    user = UserFactory()
    image = ImageFactory()
    interface = ComponentInterfaceFactory(kind=kind)

    payload = {"interface": interface.slug, "image": image.api_url}

    # test
    request = rf.get("/foo")
    request.user = user
    serializer = ComponentInterfaceValuePostSerializer(
        data=payload, context={"request": request}
    )

    # verify
    assert not serializer.is_valid()
    assert (
        "Invalid hyperlink - Object does not exist"
        in serializer.errors["image"][0]
    )


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", InterfaceKinds.panimg)
def test_civ_post_upload_session_permission_validation(kind, rf):
    # setup
    user = UserFactory()
    upload = UploadSessionFactory()
    interface = ComponentInterfaceFactory(kind=kind)

    payload = {"interface": interface.slug, "upload_session": upload.api_url}

    # test
    request = rf.get("/foo")
    request.user = user
    serializer = ComponentInterfaceValuePostSerializer(
        data=payload, context={"request": request}
    )

    # verify
    assert not serializer.is_valid()
    assert (
        "Invalid hyperlink - Object does not exist"
        in serializer.errors["upload_session"][0]
    )


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", InterfaceKinds.dicom)
def test_civ_post_dicom_uploads_permission_validation(kind, rf):
    user = UserFactory()
    uploads = UserUploadFactory.create_batch(2)
    interface = ComponentInterfaceFactory(kind=kind)
    payload = {
        "interface": interface.slug,
        "user_uploads": [upload.api_url for upload in uploads],
        "image_name": "foobar",
    }
    request = rf.get("/foo")
    request.user = user

    serializer = ComponentInterfaceValuePostSerializer(
        data=payload, context={"request": request}
    )

    assert not serializer.is_valid()
    assert (
        "Invalid hyperlink - Object does not exist"
        in serializer.errors["user_uploads"][0]
    )


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", InterfaceKinds.image)
def test_civ_post_image_not_ready_validation(kind, rf):
    # setup
    user = UserFactory()
    upload = UploadSessionFactory(
        status=RawImageUploadSession.REQUEUED, creator=user
    )
    interface = ComponentInterfaceFactory(kind=kind)

    payload = {"interface": interface.slug, "upload_session": upload.api_url}

    # test
    request = rf.get("/foo")
    request.user = user
    serializer = ComponentInterfaceValuePostSerializer(
        data=payload, context={"request": request}
    )

    # verify
    assert not serializer.is_valid()
    assert (
        "Invalid hyperlink - Object does not exist"
        in serializer.errors["upload_session"][0]
    )


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", InterfaceKinds.dicom)
def test_civ_post_dicom_image_valid(kind, rf):
    user = UserFactory()
    dicom_image_set = DICOMImageSetFactory()
    image = ImageFactory(dicom_image_set=dicom_image_set)
    assign_perm("view_image", user, image)
    interface = ComponentInterfaceFactory(kind=kind)
    payload = {"interface": interface.slug, "image": image.api_url}
    request = rf.get("/foo")
    request.user = user

    serializer = ComponentInterfaceValuePostSerializer(
        data=payload, context={"request": request}
    )

    assert serializer.is_valid()


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", InterfaceKinds.panimg)
def test_civ_post_panimg_image_valid(kind, rf):
    user = UserFactory()
    image = ImageFactory(
        name="foobar", color_space="GRAY", depth=1, timepoints=3
    )
    assign_perm("view_image", user, image)
    interface = ComponentInterfaceFactory(kind=kind)
    payload = {"interface": interface.slug, "image": image.api_url}
    request = rf.get("/foo")
    request.user = user

    serializer = ComponentInterfaceValuePostSerializer(
        data=payload, context={"request": request}
    )

    assert serializer.is_valid(), f"{serializer.errors}"


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", InterfaceKinds.panimg)
def test_civ_post_image_upload_session_valid(kind, rf):
    # setup
    user = UserFactory()
    upload = UploadSessionFactory(
        status=RawImageUploadSession.PENDING, creator=user
    )
    interface = ComponentInterfaceFactory(kind=kind)

    payload = {"interface": interface.slug, "upload_session": upload.api_url}

    # test
    request = rf.get("/foo")
    request.user = user
    serializer = ComponentInterfaceValuePostSerializer(
        data=payload, context={"request": request}
    )

    # verify
    assert serializer.is_valid(), f"{serializer.errors}"


@pytest.mark.django_db
@pytest.mark.parametrize("kind,", InterfaceKinds.dicom)
def test_civ_post_dicom_image_upload_valid(kind, rf):
    user = UserFactory()
    uploads = UserUploadFactory.create_batch(2, creator=user)
    interface = ComponentInterfaceFactory(kind=kind)
    payload = {
        "interface": interface.slug,
        "user_uploads": [upload.api_url for upload in uploads],
        "image_name": "foobar",
    }
    request = rf.get("/foo")
    request.user = user

    serializer = ComponentInterfaceValuePostSerializer(
        data=payload, context={"request": request}
    )

    assert serializer.is_valid(), f"{serializer.errors}"


@pytest.mark.django_db
def test_civ_serializer_list_ordering():

    civs = [
        ComponentInterfaceValueFactory(
            interface=ComponentInterfaceFactory(
                kind=InterfaceKindChoices.PANIMG_IMAGE,
                title="B Image Interface",
                store_in_database=False,
            )
        ),
        ComponentInterfaceValueFactory(
            interface=ComponentInterfaceFactory(
                kind=InterfaceKindChoices.PANIMG_IMAGE,
                title="A Image Interface",
                store_in_database=False,
            )
        ),
        ComponentInterfaceValueFactory(
            interface=ComponentInterfaceFactory(
                kind=InterfaceKindChoices.THUMBNAIL_PNG,
                store_in_database=False,
            )
        ),
        ComponentInterfaceValueFactory(
            interface=ComponentInterfaceFactory(
                kind=InterfaceKindChoices.ZIP,
                store_in_database=False,
            )
        ),
        ComponentInterfaceValueFactory(
            interface=ComponentInterfaceFactory(
                kind=InterfaceKindChoices.STRING
            ),
            value="bar",
        ),
        ComponentInterfaceValueFactory(
            interface=ComponentInterfaceFactory(
                kind=InterfaceKindChoices.CHART
            ),
            value="foo",
        ),
    ]

    serializer = ComponentInterfaceValueSerializer(many=True)

    produced_order = serializer.to_representation(
        data=ComponentInterfaceValue.objects.filter(
            pk__in=[civ.pk for civ in civs]
        )
    )

    expected_order = [
        civs[4],
        civs[2],
        civs[5],
        civs[3],
        civs[1],
        civs[0],
    ]

    assert [civ["interface"]["slug"] for civ in produced_order] == [
        civ.interface.slug for civ in expected_order
    ]
