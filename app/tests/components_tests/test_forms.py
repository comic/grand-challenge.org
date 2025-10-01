import pytest
from guardian.shortcuts import assign_perm

from grandchallenge.archives.forms import (
    ArchiveItemCreateForm,
    ArchiveItemUpdateForm,
)
from grandchallenge.components.form_fields import (
    INTERFACE_FORM_FIELD_PREFIX,
    InterfaceFormFieldFactory,
)
from grandchallenge.components.models import ComponentInterface
from grandchallenge.reader_studies.forms import (
    DisplaySetCreateForm,
    DisplaySetUpdateForm,
)
from grandchallenge.uploads.models import UserUpload
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.conftest import get_interface_form_data
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    ReaderStudyFactory,
)
from tests.uploads_tests.factories import UserUploadFactory


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
    field = InterfaceFormFieldFactory(interface=ci, user=user)
    assert im1 in field.fields[0].queryset.all()
    assert im2 not in field.fields[0].queryset.all()
    assert upload1 in field.fields[1].queryset.all()
    assert upload2 not in field.fields[1].queryset.all()


@pytest.mark.parametrize(
    "form_class,base_object_factory,extra_form_kwargs",
    (
        (
            DisplaySetCreateForm,
            ReaderStudyFactory,
            {"order": 1},
        ),
        (
            ArchiveItemCreateForm,
            ArchiveFactory,
            {},
        ),
    ),
)
@pytest.mark.django_db
def test_image_widget_current_value_in_archive_item_and_display_set_create_forms(
    form_class, base_object_factory, extra_form_kwargs
):
    user = UserFactory()
    image_ci = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.PANIMG_IMAGE
    )

    image = ImageFactory()
    assign_perm("cases.view_image", user, image)

    user_upload = UserUploadFactory(creator=user)
    user_upload.status = UserUpload.StatusChoices.COMPLETED
    user_upload.save()

    form1 = form_class(
        user=user,
        instance=None,
        base_obj=base_object_factory(),
        data={
            **extra_form_kwargs,
            **get_interface_form_data(
                interface_slug=image_ci.slug, data=image.pk, existing_data=True
            ),
        },
    )
    assert form1.is_valid()
    assert (
        form1.fields[f"{INTERFACE_FORM_FIELD_PREFIX}{image_ci.slug}"]
        .widget.attrs["current_value"][0]
        .pk
        == image.pk
    )

    form2 = form_class(
        user=user,
        instance=None,
        base_obj=base_object_factory(),
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
