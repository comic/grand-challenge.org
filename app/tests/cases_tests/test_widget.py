import pytest
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from guardian.shortcuts import assign_perm

from grandchallenge.cases.widgets import FlexibleImageField, ImageWidgetChoices
from grandchallenge.components.form_fields import InterfaceFormField
from grandchallenge.components.models import ComponentInterface
from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.uploads.models import UserUpload
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory
from tests.uploads_tests.factories import UserUploadFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_flexible_image_field_validation():
    user = UserFactory()
    upload1 = UserUploadFactory(creator=user)
    upload2 = UserUploadFactory()
    im1, im2 = ImageFactory.create_batch(2)
    assign_perm("cases.view_image", user, im1)
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)
    field = FlexibleImageField(
        image_queryset=get_objects_for_user(user, "cases.view_image"),
        upload_queryset=UserUpload.objects.filter(creator=user).all(),
    )
    parsed_value_for_empty_data = field.widget.value_from_datadict(
        data={}, name=ci.slug, files={}
    )
    decompressed_value_for_missing_value = field.widget.decompress(value=None)
    assert not parsed_value_for_empty_data
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
def test_flexible_image_widget(client):
    user = UserFactory()
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)
    response = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user,
        data={
            f"WidgetChoice-{ci.slug}": ImageWidgetChoices.IMAGE_SEARCH.name,
            "interface_slug": ci.slug,
        },
    )
    assert '<input class="form-control" type="search"' in str(response.content)

    response2 = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user,
        data={
            f"WidgetChoice-{ci.slug}": ImageWidgetChoices.IMAGE_UPLOAD.name,
            "interface_slug": ci.slug,
        },
    )
    assert 'class="user-upload"' in str(response2.content)

    response3 = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user,
        data={
            f"WidgetChoice-{ci.slug}": ImageWidgetChoices.UNDEFINED.name,
            "interface_slug": ci.slug,
        },
    )
    assert response3.content == b""

    image = ImageFactory()
    response4 = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user,
        data={
            f"WidgetChoice-{ci.slug}": ImageWidgetChoices.IMAGE_SELECTED.name,
            "interface_slug": ci.slug,
            "current_value": image.pk,
        },
    )
    assert format_html(
        '<input type="hidden" name="{}" value="{}">', ci.slug, image.pk
    ) in str(response4.content)

    user_upload = UserUploadFactory()
    response5 = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user,
        data={
            f"WidgetChoice-{ci.slug}": ImageWidgetChoices.IMAGE_SELECTED.name,
            "interface_slug": ci.slug,
            "current_value": user_upload.pk,
        },
    )
    assert format_html(
        '<input type="hidden" name="{}" value="{}">', ci.slug, user_upload.pk
    ) in str(response5.content)


@pytest.mark.django_db
def test_flexible_image_widget_prepopulated_value():
    user = UserFactory()
    im = ImageFactory(name="test_image")
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)
    civ = ComponentInterfaceValueFactory(interface=ci, image=im)
    field = InterfaceFormField(instance=ci, user=user, initial=civ)
    assert field.field.widget.attrs["current_value"] == civ.image
    assert field.field.initial == civ.image.pk
