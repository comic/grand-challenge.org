import pytest
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.cases.models import Image
from grandchallenge.components.models import ComponentInterface
from tests.cases_tests.factories import (
    ImageFactoryWithImageFile,
    ImageFactoryWithImageFile2DGray16Bit,
    ImageFactoryWithImageFile3D,
    ImageFactoryWithImageFile16Bit,
    ImageFactoryWithoutImageFile,
    RawImageUploadSessionFactory,
)
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.factories import ImageFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
class TestObjectPermissionRequiredViews:
    def test_permission_required_views(self, client):
        rius = RawImageUploadSessionFactory()
        image_file_mh = ImageFactoryWithImageFile(
            color_space=Image.COLOR_SPACE_GRAY
        )
        u = UserFactory()

        for view_name, kwargs, permission, obj in [
            (
                "raw-image-upload-session-detail",
                {"pk": rius.pk},
                "view_rawimageuploadsession",
                rius,
            ),
            (
                "vtk-image-detail",
                {"pk": image_file_mh.pk},
                "view_image",
                image_file_mh,
            ),
            (
                "cs-image-detail",
                {"pk": image_file_mh.pk},
                "view_image",
                image_file_mh,
            ),
        ]:
            response = get_view_for_user(
                client=client,
                viewname=f"cases:{view_name}",
                reverse_kwargs=kwargs,
                user=u,
            )

            assert response.status_code == 403

            assign_perm(permission, u, obj)

            response = get_view_for_user(
                client=client,
                viewname=f"cases:{view_name}",
                reverse_kwargs=kwargs,
                user=u,
            )

            assert response.status_code == 200

            remove_perm(permission, u, obj)

    def test_permission_filtered_views(self, client):
        rius = RawImageUploadSessionFactory()
        u = UserFactory()

        for view_name, kwargs, permission, obj in [
            (
                "raw-image-upload-session-list",
                {},
                "view_rawimageuploadsession",
                rius,
            )
        ]:
            assign_perm(permission, u, obj)

            response = get_view_for_user(
                client=client,
                viewname=f"cases:{view_name}",
                reverse_kwargs=kwargs,
                user=u,
            )

            assert response.status_code == 200
            assert obj in response.context[-1]["object_list"]

            remove_perm(permission, u, obj)

            response = get_view_for_user(
                client=client,
                viewname=f"cases:{view_name}",
                reverse_kwargs=kwargs,
                user=u,
            )

            assert response.status_code == 200
            assert obj not in response.context[-1]["object_list"]


@pytest.mark.django_db
class TestVTKImageDetail:
    def test_permission_required_views(self, client):
        def get_status_code(image):
            u = UserFactory()
            assign_perm("view_image", u, image)
            response = get_view_for_user(
                client=client,
                viewname="cases:vtk-image-detail",
                reverse_kwargs={"pk": image.pk},
                user=u,
            )
            return response.status_code

        for image in (
            ImageFactoryWithoutImageFile(color_space=Image.COLOR_SPACE_GRAY),
            ImageFactoryWithImageFile(color_space=Image.COLOR_SPACE_RGB),
            ImageFactoryWithImageFile(color_space=Image.COLOR_SPACE_RGBA),
            ImageFactoryWithImageFile(color_space=Image.COLOR_SPACE_YCBCR),
        ):
            assert get_status_code(image) == 404

        image = ImageFactoryWithImageFile(color_space=Image.COLOR_SPACE_GRAY)
        assert get_status_code(image) == 200


P = "patient_id__isempty"
S = "study_description__isempty"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "factory_kwargs,data_non_filtered,data_filtered",
    (
        (
            {},
            ({}, {P: True}, {S: True}, {P: True, S: True}),
            ({P: False}, {S: False}, {P: False, S: False}),
        ),
        (
            {"patient_id": "test"},
            ({}, {P: False}, {S: True}, {P: False, S: True}),
            ({P: True}, {S: False}, {P: True, S: False}),
        ),
        (
            {"study_description": "test"},
            ({}, {P: True}, {S: False}, {P: True, S: False}),
            ({P: False}, {S: True}, {P: False, S: True}),
        ),
        (
            {"study_description": "test", "patient_id": "test"},
            ({}, {P: False}, {S: False}, {P: False, S: False}),
            ({P: True}, {S: True}, {P: True, S: True}),
        ),
    ),
)
def test_imageviewset_empty_fields_filtering(
    client, factory_kwargs, data_non_filtered, data_filtered
):
    image = ImageFactory(**factory_kwargs)
    u = UserFactory()
    assign_perm("view_image", u, image)
    view_kwargs = {"client": client, "viewname": "api:image-list", "user": u}
    for data in data_non_filtered:
        response = get_view_for_user(**view_kwargs, data=data)
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["pk"] == str(image.pk)

    for data in data_filtered:
        response = get_view_for_user(**view_kwargs, data=data)
        assert response.status_code == 200
        assert len(response.data["results"]) == 0


@pytest.mark.django_db
class TestCSImageDetail:
    def get_status_code(self, client, viewname, image):
        u = UserFactory()
        assign_perm("view_image", u, image)
        response = get_view_for_user(
            client=client,
            viewname=f"cases:{viewname}-image-detail",
            reverse_kwargs={"pk": image.pk},
            user=u,
        )
        return response.status_code

    @pytest.mark.parametrize(
        "viewname,factory,kwargs",
        [
            (
                "cs",
                ImageFactoryWithoutImageFile,
                {"color_space": Image.COLOR_SPACE_GRAY},
            ),
            (
                "cs3d",
                ImageFactoryWithoutImageFile,
                {"color_space": Image.COLOR_SPACE_GRAY},
            ),
            (
                "cs",
                ImageFactoryWithImageFile,
                {"color_space": Image.COLOR_SPACE_YCBCR},
            ),
        ],
    )
    def test_not_allowed(self, client, viewname, factory, kwargs):
        assert self.get_status_code(client, viewname, factory(**kwargs)) == 404

    @pytest.mark.parametrize("viewname", ["cs", "cs3d"])
    @pytest.mark.parametrize(
        "factory,kwargs",
        [
            (ImageFactoryWithImageFile2DGray16Bit, {}),
            (
                ImageFactoryWithImageFile,
                {"color_space": Image.COLOR_SPACE_RGB},
            ),
            (
                ImageFactoryWithImageFile,
                {"color_space": Image.COLOR_SPACE_RGBA},
            ),
            (ImageFactoryWithImageFile16Bit, {}),
            (ImageFactoryWithImageFile3D, {}),
        ],
    )
    def test_allowed(self, client, viewname, factory, kwargs):
        assert self.get_status_code(client, viewname, factory(**kwargs)) == 200


@pytest.mark.django_db
def test_image_search_view(client):
    user = UserFactory()
    im1, im2, im3 = ImageFactory.create_batch(3)
    assign_perm("cases.view_image", user, im1)
    assign_perm("cases.view_image", user, im2)
    im2.name = "test.mha"
    im2.save()
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)

    response = get_view_for_user(
        viewname="cases:image-search",
        client=client,
        user=user,
        data={
            "interface_slug": ci.slug,
            f"query-{ci.slug}": "test",
        },
    )
    assert response.status_code == 200
    assert len(response.context_data["object_list"]) == 1
    assert response.context_data["object_list"].get() == im2

    response = get_view_for_user(
        viewname="cases:image-search",
        client=client,
        user=user,
        data={
            "interface_slug": ci.slug,
            f"query-{ci.slug}": "",
        },
    )
    assert response.status_code == 200
    assert len(response.context_data["object_list"]) == 2
    assert im1 in response.context_data["object_list"].all()
    assert im2 in response.context_data["object_list"].all()
    assert im3 not in response.context_data["object_list"].all()
