import pytest
from django.core.exceptions import ValidationError
from guardian.shortcuts import assign_perm

from grandchallenge.archives.forms import ArchiveItemUpdateForm
from grandchallenge.components.forms import (
    INTERFACE_FORM_FIELD_PREFIX,
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
    upload1 = UserUploadFactory(creator=user)
    upload2 = UserUploadFactory()
    upload1.status = UserUpload.StatusChoices.COMPLETED
    upload1.save()
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.PANIMG_IMAGE)
    fields = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci, user=user
    )
    assert len(fields) == 1
    field = fields[f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}"]
    assert im1 in field.fields[0].queryset.all()
    assert im2 not in field.fields[0].queryset.all()
    assert upload1 in field.fields[1].queryset.all()
    assert upload2 not in field.fields[1].queryset.all()


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
def test_image_widget_current_value_in_archive_item_and_display_set_update_forms(
    form_class, object_factory, extra_form_kwargs
):
    user = UserFactory()
    image_ci = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.PANIMG_IMAGE
    )

    image1 = ImageFactory()
    assign_perm("cases.view_image", user, image1)
    image_civ = ComponentInterfaceValueFactory(
        interface=image_ci, image=image1
    )
    instance = object_factory()
    instance.values.set([image_civ])

    image2 = ImageFactory()
    assign_perm("cases.view_image", user, image2)

    user_upload = UserUploadFactory(creator=user)
    user_upload.status = UserUpload.StatusChoices.COMPLETED
    user_upload.save()

    form1 = form_class(
        user=user,
        instance=instance,
        base_obj=instance.base_object,
        data={
            **extra_form_kwargs,
            **get_interface_form_data(
                interface_slug=image_ci.slug,
                data=image2.pk,
                existing_data=True,
            ),
        },
    )
    assert form1.is_valid()
    assert (
        form1.fields[f"{INTERFACE_FORM_FIELD_PREFIX}{image_ci.slug}"]
        .widget.attrs["current_value"][0]
        .pk
        == image2.pk
    )

    form2 = form_class(
        user=user,
        instance=instance,
        base_obj=instance.base_object,
        data={
            **extra_form_kwargs,
            **get_interface_form_data(
                interface_slug=image_ci.slug, data=user_upload.pk
            ),
        },
    )
    assert form2.is_valid()
    assert (
        form2.fields[f"{INTERFACE_FORM_FIELD_PREFIX}{image_ci.slug}"]
        .widget.attrs["current_value"][0]
        .pk
        == user_upload.pk
    )


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
        data=["an image name", [upload]],
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
    ci = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.DICOM_IMAGE_SET
    )
    fields = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci, user=user
    )
    assert len(fields) == 4
    field = fields[f"{FlexibleWidgetPrefixes.SEARCH}{ci.slug}"]

    assert field.clean(["", str(dicom_image.pk)]) == dicom_image
    with pytest.raises(ValidationError):
        field.clean(["", str(panimg_image.pk)])


@pytest.mark.django_db
def test_interface_form_field_image_search_validates_permission():
    user = UserFactory()
    dicom_image = ImageFactory(dicom_image_set=DICOMImageSetFactory())
    assign_perm("cases.view_image", user, dicom_image)
    dicom_image_no_perm = ImageFactory(dicom_image_set=DICOMImageSetFactory())
    ci = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.DICOM_IMAGE_SET
    )
    fields = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci, user=user
    )
    assert len(fields) == 4
    field = fields[f"{FlexibleWidgetPrefixes.SEARCH}{ci.slug}"]

    assert field.clean(["", str(dicom_image.pk)]) == dicom_image
    with pytest.raises(ValidationError):
        field.clean(["", str(dicom_image_no_perm.pk)])
