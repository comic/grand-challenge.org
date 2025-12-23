import pytest
from django.utils.html import format_html
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.cases.widgets import ImageWidgetChoices
from grandchallenge.components.forms import INTERFACE_FORM_FIELD_PREFIX
from grandchallenge.components.models import ComponentInterface
from tests.cases_tests.factories import (
    DICOMImageSetFactory,
    DICOMImageSetUploadFactory,
    RawImageUploadSessionFactory,
)
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.factories import ImageFactory, UserFactory
from tests.uploads_tests.factories import UserUploadFactory
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
    images = ImageFactory.create_batch(3)
    dicom_image_sets = DICOMImageSetFactory.create_batch(3)
    images_dicom = [
        ImageFactory(dicom_image_set=dicom_image_set)
        for dicom_image_set in dicom_image_sets
    ]
    for image in (images[0], images[1], images_dicom[0], images_dicom[1]):
        assign_perm("cases.view_image", user, image)
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

    response = get_view_for_user(
        viewname="cases:image-search",
        client=client,
        user=user,
        data={
            "prefixed-interface-slug": ci_panimg.slug,
            f"query-{ci_panimg.slug}": "test",
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
            f"query-{ci_panimg.slug}": "",
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
            f"query-{ci_dicom.slug}": "test",
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
            f"query-{ci_dicom.slug}": "",
        },
    )
    assert response.status_code == 200
    assert len(response.context_data["object_list"]) == 2
    assert images_dicom[0] in response.context_data["object_list"].all()
    assert images_dicom[1] in response.context_data["object_list"].all()
    assert images_dicom[2] not in response.context_data["object_list"].all()
    for image in images:
        assert image not in response.context_data["object_list"].all()


@pytest.mark.django_db
def test_image_widget_select_view(client):
    user = UserFactory()
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.PANIMG_IMAGE)
    response = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": ImageWidgetChoices.IMAGE_SEARCH.value,
            "prefixed-interface-slug": ci.slug,
        },
    )
    assert '<input class="form-control" type="search"' in str(response.content)

    response2 = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": ImageWidgetChoices.IMAGE_UPLOAD.value,
            "prefixed-interface-slug": ci.slug,
        },
    )
    assert 'class="user-upload"' in str(response2.content)

    response3 = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": ImageWidgetChoices.UNDEFINED.value,
            "prefixed-interface-slug": ci.slug,
        },
    )
    assert response3.content == b""


@pytest.mark.django_db
def test_image_widget_select_view_image_selected_object_permission(client):
    user_with_perm, user_wo_perm = UserFactory.create_batch(2)
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.PANIMG_IMAGE)
    prefixed_interface_slug = f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}"
    image = ImageFactory()
    assign_perm("cases.view_image", user_with_perm, image)

    response_user_with_perm = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user_with_perm,
        data={
            f"widget-choice-{prefixed_interface_slug}": ImageWidgetChoices.IMAGE_SELECTED.name,
            "prefixed-interface-slug": prefixed_interface_slug,
            "current-value-pk": image.pk,
        },
    )
    assert format_html(
        '<input type="hidden" name="{}" value="{}">',
        prefixed_interface_slug,
        image.pk,
    ) in str(response_user_with_perm.content)

    response_user_wo_perm = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user_wo_perm,
        data={
            f"widget-choice-{prefixed_interface_slug}": ImageWidgetChoices.IMAGE_SELECTED.name,
            "prefixed-interface-slug": prefixed_interface_slug,
            "current-value-pk": image.pk,
        },
    )
    assert response_user_wo_perm.status_code == 404


@pytest.mark.django_db
def test_file_widget_select_view_file_selected_object_permission_user_upload(
    client,
):
    user, creator = UserFactory.create_batch(2)
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.PANIMG_IMAGE)
    prefixed_interface_slug = f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}"
    user_upload = UserUploadFactory(creator=creator)

    response_creator = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=creator,
        data={
            f"widget-choice-{prefixed_interface_slug}": ImageWidgetChoices.IMAGE_SELECTED.name,
            "prefixed-interface-slug": prefixed_interface_slug,
            "current-value-pk": user_upload.pk,
        },
    )
    assert format_html(
        '<input type="hidden" name="{}" value="{}">',
        prefixed_interface_slug,
        user_upload.pk,
    ) in str(response_creator.content)

    response_user = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user,
        data={
            f"widget-choice-{prefixed_interface_slug}": ImageWidgetChoices.IMAGE_SELECTED.name,
            "prefixed-interface-slug": prefixed_interface_slug,
            "current-value-pk": user_upload.pk,
        },
    )
    assert response_user.status_code == 404
