import pytest
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.components.forms import FlexibleWidgetPrefixes
from grandchallenge.components.models import ComponentInterface
from grandchallenge.components.widgets import SearchWidgetSuffixes
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.cases_tests.factories import (
    DICOMImageSetFactory,
    DICOMImageSetUploadFactory,
    RawImageUploadSessionFactory,
)
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
class TestObjectPermissionRequiredViews:
    def test_permission_required_views(self, client):
        rius = RawImageUploadSessionFactory()
        dicom_image_set_upload = DICOMImageSetUploadFactory()
        u = UserFactory()

        for view_name, kwargs, permission, obj in [
            (
                "raw-image-upload-session-detail",
                {"pk": rius.pk},
                "view_rawimageuploadsession",
                rius,
            ),
            (
                "dicom-image-set-upload-detail",
                {"pk": dicom_image_set_upload.pk},
                "view_dicomimagesetupload",
                dicom_image_set_upload,
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
        dicom_image_set_upload = DICOMImageSetUploadFactory()
        u = UserFactory()

        for view_name, kwargs, permission, obj in [
            (
                "raw-image-upload-session-list",
                {},
                "view_rawimageuploadsession",
                rius,
            ),
            (
                "dicom-image-set-upload-list",
                {},
                "view_dicomimagesetupload",
                dicom_image_set_upload,
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
def test_image_search_view(client):
    user = UserFactory()
    archive = ArchiveFactory()
    archive.add_user(user)
    ai = ArchiveItemFactory(archive=archive)

    images = ImageFactory.create_batch(3)
    dicom_image_sets = DICOMImageSetFactory.create_batch(3)
    images_dicom = [
        ImageFactory(dicom_image_set=dicom_image_set)
        for dicom_image_set in dicom_image_sets
    ]
    images[1].name = "test.mha"
    images[1].save()
    images_dicom[1].name = "test.dcm"
    images_dicom[1].save()

    ci_panimg = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.PANIMG_IMAGE
    )
    ci_dicom = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.DICOM_IMAGE_SET
    )
    for image in (images[0], images[1]):
        # add to archive item that the user has view permission for
        civ = ComponentInterfaceValueFactory(interface=ci_panimg, image=image)
        ai.values.add(civ)

    for image in (images_dicom[0], images_dicom[1]):
        # add to archive item that the user has view permission for
        civ = ComponentInterfaceValueFactory(interface=ci_dicom, image=image)
        ai.values.add(civ)

    response = get_view_for_user(
        viewname="cases:image-search",
        client=client,
        user=user,
        data={
            "prefixed-interface-slug": ci_panimg.slug,
            f"{FlexibleWidgetPrefixes.SEARCH}{ci_panimg.slug}_{SearchWidgetSuffixes.INPUT}": "test",
        },
    )
    assert response.status_code == 200
    assert response.context_data["object_list"].get() == images[1]

    response = get_view_for_user(
        viewname="cases:image-search",
        client=client,
        user=user,
        data={
            "prefixed-interface-slug": ci_panimg.slug,
            f"{FlexibleWidgetPrefixes.SEARCH}{ci_panimg.slug}_{SearchWidgetSuffixes.INPUT}": "",
        },
    )
    assert response.status_code == 200
    assert len(response.context_data["object_list"]) == 2
    assert images[0] in response.context_data["object_list"].all()
    assert images[1] in response.context_data["object_list"].all()
    assert images[2] not in response.context_data["object_list"].all()
    for image in images_dicom:
        assert image not in response.context_data["object_list"].all()

    response = get_view_for_user(
        viewname="cases:image-search",
        client=client,
        user=user,
        data={
            "prefixed-interface-slug": ci_dicom.slug,
            f"{FlexibleWidgetPrefixes.SEARCH}{ci_dicom.slug}_{SearchWidgetSuffixes.INPUT}": "test",
        },
    )
    assert response.status_code == 200
    assert response.context_data["object_list"].get() == images_dicom[1]

    response = get_view_for_user(
        viewname="cases:image-search",
        client=client,
        user=user,
        data={
            "prefixed-interface-slug": ci_dicom.slug,
            f"{FlexibleWidgetPrefixes.SEARCH}{ci_dicom.slug}_{SearchWidgetSuffixes.INPUT}": "",
        },
    )
    assert response.status_code == 200
    assert len(response.context_data["object_list"]) == 2
    assert images_dicom[0] in response.context_data["object_list"].all()
    assert images_dicom[1] in response.context_data["object_list"].all()
    assert images_dicom[2] not in response.context_data["object_list"].all()
    for image in images:
        assert image not in response.context_data["object_list"].all()
