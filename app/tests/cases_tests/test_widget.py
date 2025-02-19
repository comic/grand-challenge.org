import pytest
from django.core.exceptions import ValidationError
from guardian.shortcuts import assign_perm

from grandchallenge.cases.widgets import FlexibleImageField
from grandchallenge.components.form_fields import InterfaceFormFieldFactory
from grandchallenge.components.models import ComponentInterface
from grandchallenge.uploads.models import UserUpload
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory
from tests.uploads_tests.factories import UserUploadFactory


@pytest.mark.django_db
def test_flexible_image_field_validation():
    user = UserFactory()
    upload1 = UserUploadFactory(creator=user)
    upload1.status = UserUpload.StatusChoices.COMPLETED
    upload1.save()
    upload2 = UserUploadFactory()
    upload2.status = UserUpload.StatusChoices.COMPLETED
    upload2.save()
    im1, im2 = ImageFactory.create_batch(2)
    assign_perm("cases.view_image", user, im1)
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)
    field = FlexibleImageField(user=user)
    parsed_value_for_empty_data = field.widget.value_from_datadict(
        data={}, name=ci.slug, files={}
    )
    decompressed_value_for_missing_value = field.widget.decompress(value=None)
    assert parsed_value_for_empty_data == [None, None]
    assert decompressed_value_for_missing_value == [None, None]

    parsed_value_for_image_with_permission = field.widget.value_from_datadict(
        data={ci.slug: im1.pk}, name=ci.slug, files={}
    )
    decompressed_value_for_image_with_permission = field.widget.decompress(
        im1.pk
    )
    assert (
        parsed_value_for_image_with_permission
        == decompressed_value_for_image_with_permission
        == [
            im1.pk,
            None,
        ]
    )
    assert field.clean(parsed_value_for_image_with_permission) == im1

    parsed_value_for_image_without_permission = (
        field.widget.value_from_datadict(
            data={ci.slug: im2.pk}, name=ci.slug, files={}
        )
    )
    decompressed_value_for_image_without_permission = field.widget.decompress(
        im2.pk
    )
    assert (
        parsed_value_for_image_without_permission
        == decompressed_value_for_image_without_permission
        == [im2.pk, None]
    )
    with pytest.raises(ValidationError):
        field.clean(parsed_value_for_image_without_permission)

    parsed_value_for_upload_from_user = field.widget.value_from_datadict(
        data={ci.slug: str(upload1.pk)}, name=ci.slug, files={}
    )
    decompressed_value_for_upload_from_user = field.widget.decompress(
        str(upload1.pk)
    )
    assert (
        parsed_value_for_upload_from_user
        == decompressed_value_for_upload_from_user
        == [None, [str(upload1.pk)]]
    )
    assert field.clean(parsed_value_for_upload_from_user).get() == upload1

    parsed_value_from_upload_from_other_user = (
        field.widget.value_from_datadict(
            data={ci.slug: str(upload2.pk)}, name=ci.slug, files={}
        )
    )
    decompressed_value_for_upload_from_other_user = field.widget.decompress(
        str(upload2.pk)
    )
    assert (
        parsed_value_from_upload_from_other_user
        == decompressed_value_for_upload_from_other_user
        == [None, [str(upload2.pk)]]
    )
    with pytest.raises(ValidationError):
        field.clean(parsed_value_from_upload_from_other_user)

    parsed_value_for_missing_value = field.widget.value_from_datadict(
        data={ci.slug: "IMAGE_UPLOAD"}, name=ci.slug, files={}
    )
    decompressed_value_for_missing_value = field.widget.decompress(
        "IMAGE_UPLOAD"
    )
    assert (
        parsed_value_for_missing_value
        == decompressed_value_for_missing_value
        == [None, None]
    )
    with pytest.raises(ValidationError):
        field.clean(parsed_value_for_missing_value)


@pytest.mark.django_db
def test_flexible_image_widget_prepopulated_value():
    user_with_perm, user_without_perm = UserFactory.create_batch(2)
    im = ImageFactory(name="test_image")
    assign_perm("cases.view_image", user_with_perm, im)
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)
    civ = ComponentInterfaceValueFactory(interface=ci, image=im)

    field = InterfaceFormFieldFactory(
        interface=ci, user=user_with_perm, initial=civ
    )
    assert field.widget.attrs["current_value"] == civ.image
    assert field.initial == civ.image.pk

    field = InterfaceFormFieldFactory(
        interface=ci, user=user_with_perm, initial=civ.image.pk
    )
    assert field.widget.attrs["current_value"] == civ.image
    assert field.initial == civ.image.pk

    field = InterfaceFormFieldFactory(
        interface=ci, user=user_without_perm, initial=civ
    )
    assert field.widget.attrs["current_value"] is None
    assert field.initial is None

    field = InterfaceFormFieldFactory(
        interface=ci, user=user_without_perm, initial=civ.image.pk
    )
    assert field.widget.attrs["current_value"] is None
    assert field.initial is None
