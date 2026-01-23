import pytest
from django.core.exceptions import ValidationError
from guardian.shortcuts import assign_perm

from grandchallenge.archives.forms import ArchiveItemUpdateForm
from grandchallenge.components.forms import (
    FlexibleWidgetPrefixes,
    InterfaceFormFieldsMixin,
)
from grandchallenge.components.models import (
    ComponentInterface,
    InterfaceKindChoices,
)
from grandchallenge.reader_studies.forms import DisplaySetUpdateForm
from grandchallenge.uploads.models import UserUpload
from tests.archives_tests.factories import ArchiveItemFactory
from tests.cases_tests.factories import DICOMImageSetFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.conftest import get_interface_form_data
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import DisplaySetFactory
from tests.uploads_tests.factories import (
    UserUploadFactory,
    create_completed_upload,
)


@pytest.mark.django_db
def test_interface_form_field_image_queryset_filter():
    user = UserFactory()
    im1, im2 = ImageFactory.create_batch(2)
    assign_perm("cases.view_image", user, im1)
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.PANIMG_IMAGE)
    field = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci, user=user
    )[f"{FlexibleWidgetPrefixes.SEARCH}{ci.slug}"]

    assert im1 in field.fields[1].queryset.all()
    assert im2 not in field.fields[1].queryset.all()
    assert field.clean(["", str(im1.pk)]) == im1
    with pytest.raises(ValidationError):
        field.clean(["", str(im2.pk)])


@pytest.mark.django_db
def test_interface_form_field_image_upload_validation():
    user = UserFactory()
    upload = UserUploadFactory(creator=user)
    upload.status = UserUpload.StatusChoices.COMPLETED
    upload.save()
    upload_from_other_user = UserUploadFactory()
    upload_from_other_user.status = UserUpload.StatusChoices.COMPLETED
    upload_from_other_user.save()
    pending_upload = UserUploadFactory(creator=user)
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.PANIMG_IMAGE)
    field = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci, user=user
    )[f"{FlexibleWidgetPrefixes.UPLOAD}{ci.slug}"]

    assert upload in field.queryset.all()
    assert upload_from_other_user not in field.queryset.all()
    assert pending_upload not in field.queryset.all()

    cleaned_data = field.clean([str(upload.pk)])

    assert cleaned_data.count() == 1
    assert cleaned_data.first() == upload
    with pytest.raises(ValidationError):
        field.clean([str(upload_from_other_user.pk)])
    with pytest.raises(ValidationError):
        field.clean([str(pending_upload.pk)])


@pytest.mark.parametrize(
    "form_class,object_factory,extra_form_kwargs",
    (
        (
            DisplaySetUpdateForm,
            DisplaySetFactory,
            {"order": 1},
        ),
        (
            ArchiveItemUpdateForm,
            ArchiveItemFactory,
            {},
        ),
    ),
)
@pytest.mark.django_db
def test_image_widget_current_socket_value_in_archive_item_and_display_set_update_forms(
    form_class, object_factory, extra_form_kwargs
):
    user = UserFactory()
    image_ci = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.PANIMG_IMAGE
    )

    image = ImageFactory()
    assign_perm("cases.view_image", user, image)
    image_civ = ComponentInterfaceValueFactory(interface=image_ci, image=image)
    instance = object_factory()
    instance.values.set([image_civ])

    form1 = form_class(
        user=user,
        instance=instance,
        base_obj=instance.base_object,
    )
    assert (
        form1.fields[
            f"{FlexibleWidgetPrefixes.CHOICE}{image_ci.slug}"
        ].current_socket_value
        == image_civ
    )


@pytest.mark.django_db
def test_interface_form_field_file_upload_validation():
    user = UserFactory()
    upload = UserUploadFactory(creator=user)
    upload.status = UserUpload.StatusChoices.COMPLETED
    upload.save()
    upload_from_other_user = UserUploadFactory()
    upload_from_other_user.status = UserUpload.StatusChoices.COMPLETED
    upload_from_other_user.save()
    pending_upload = UserUploadFactory(creator=user)
    ci = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY, store_in_database=False
    )
    field = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci, user=user
    )[f"{FlexibleWidgetPrefixes.UPLOAD}{ci.slug}"]

    assert upload in field.queryset.all()
    assert upload_from_other_user not in field.queryset.all()
    assert pending_upload not in field.queryset.all()
    assert field.clean(str(upload.pk)) == upload
    with pytest.raises(ValidationError):
        field.clean(str(upload_from_other_user.pk))
    with pytest.raises(ValidationError):
        field.clean(str(pending_upload.pk))


@pytest.mark.parametrize(
    "form_class,object_factory,extra_form_kwargs",
    (
        (
            DisplaySetUpdateForm,
            DisplaySetFactory,
            {"order": 1},
        ),
        (
            ArchiveItemUpdateForm,
            ArchiveItemFactory,
            {},
        ),
    ),
)
@pytest.mark.django_db
def test_dicom_widget_in_archive_item_and_display_set_update_forms(
    form_class, object_factory, extra_form_kwargs
):
    user = UserFactory()
    upload = create_completed_upload(user=user)
    socket = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.DICOM_IMAGE_SET
    )
    instance = object_factory()
    form_data = get_interface_form_data(
        interface_slug=socket.slug,
        data=["an image name", [upload.pk]],
    )

    form = form_class(
        user=user,
        instance=instance,
        base_obj=instance.base_object,
        data={
            **extra_form_kwargs,
            **form_data,
        },
    )
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_interface_form_field_image_search_validates_image_dicom_kind():
    user = UserFactory()
    dicom_image = ImageFactory(dicom_image_set=DICOMImageSetFactory())
    assign_perm("cases.view_image", user, dicom_image)
    panimg_image = ImageFactory()
    assign_perm("cases.view_image", user, panimg_image)
    ci_dicom = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.DICOM_IMAGE_SET
    )
    ci_panimg = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.PANIMG_IMAGE
    )
    dicom_field = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci_dicom, user=user
    )[f"{FlexibleWidgetPrefixes.SEARCH}{ci_dicom.slug}"]
    panimg_field = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci_panimg, user=user
    )[f"{FlexibleWidgetPrefixes.SEARCH}{ci_panimg.slug}"]

    assert dicom_field.clean(["", str(dicom_image.pk)]) == dicom_image
    with pytest.raises(ValidationError):
        dicom_field.clean(["", str(panimg_image.pk)])
    assert panimg_field.clean(["", str(panimg_image.pk)]) == panimg_image
    with pytest.raises(ValidationError):
        panimg_field.clean(["", str(dicom_image.pk)])


@pytest.mark.django_db
def test_interface_form_field_image_search_validates_permission():
    user = UserFactory()
    dicom_image = ImageFactory(dicom_image_set=DICOMImageSetFactory())
    assign_perm("cases.view_image", user, dicom_image)
    dicom_image_no_perm = ImageFactory(dicom_image_set=DICOMImageSetFactory())
    panimg_image = ImageFactory()
    assign_perm("cases.view_image", user, panimg_image)
    panimg_image_no_perm = ImageFactory()
    ci_dicom = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.DICOM_IMAGE_SET
    )
    ci_panimg = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.PANIMG_IMAGE
    )
    dicom_field = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci_dicom, user=user
    )[f"{FlexibleWidgetPrefixes.SEARCH}{ci_dicom.slug}"]
    panimg_field = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci_panimg, user=user
    )[f"{FlexibleWidgetPrefixes.SEARCH}{ci_panimg.slug}"]

    assert dicom_field.clean(["", str(dicom_image.pk)]) == dicom_image
    with pytest.raises(ValidationError):
        dicom_field.clean(["", str(dicom_image_no_perm.pk)])
    assert panimg_field.clean(["", str(panimg_image.pk)]) == panimg_image
    with pytest.raises(ValidationError):
        panimg_field.clean(["", str(panimg_image_no_perm.pk)])
