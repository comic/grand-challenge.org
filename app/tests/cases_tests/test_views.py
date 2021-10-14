import pytest
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.cases.models import Image
from tests.cases_tests.factories import (
    ImageFactoryWithImageFile,
    ImageFactoryWithoutImageFile,
    RawImageUploadSessionFactory,
)
from tests.factories import ImageFileFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
class TestObjectPermissionRequiredViews:
    def test_permission_required_views(self, client):
        rius = RawImageUploadSessionFactory()
        image_file_dzi = ImageFileFactory(image_type="DZI")
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
                "osd-image-detail",
                {"pk": image_file_dzi.image.pk},
                "view_image",
                image_file_dzi.image,
            ),
            (
                "vtk-image-detail",
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
            ),
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
