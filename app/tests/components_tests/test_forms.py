import pytest
from guardian.shortcuts import assign_perm

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.archives.forms import (
    ArchiveItemCreateForm,
    ArchiveItemUpdateForm,
)
from grandchallenge.components.form_fields import (
    INTERFACE_FORM_FIELD_PREFIX,
    InterfaceFormFieldFactory,
)
from grandchallenge.components.forms import ContainerImageForm
from grandchallenge.components.models import ComponentInterface
from grandchallenge.evaluation.models import Method
from grandchallenge.reader_studies.forms import (
    DisplaySetCreateForm,
    DisplaySetUpdateForm,
)
from grandchallenge.uploads.models import UserUpload
from grandchallenge.workstations.models import WorkstationImage
from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.conftest import get_interface_form_data
from tests.evaluation_tests.factories import MethodFactory
from tests.factories import ImageFactory, UserFactory, WorkstationImageFactory
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    ReaderStudyFactory,
)
from tests.uploads_tests.factories import UserUploadFactory
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
def test_interface_form_field_image_queryset_filter():
    user = UserFactory()
    im1, im2 = ImageFactory.create_batch(2)
    assign_perm("cases.view_image", user, im1)
    upload1 = UserUploadFactory(creator=user)
    upload2 = UserUploadFactory()
    upload1.status = UserUpload.StatusChoices.COMPLETED
    upload1.save()
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)
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
    image_ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)

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
        .widget.attrs["current_value"]
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
        .widget.attrs["current_value"]
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
    image_ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)

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
        .widget.attrs["current_value"]
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
        .widget.attrs["current_value"]
        .pk
        == user_upload.pk
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "meta_model, factory",
    (
        (AlgorithmImage, AlgorithmImageFactory),
        (Method, MethodFactory),
        (WorkstationImage, WorkstationImageFactory),
    ),
)
def test_container_image_form_invalid_with_already_assigned_used_upload(
    meta_model,
    factory,
):
    class TestForm(ContainerImageForm):
        class Meta(ContainerImageForm.Meta):
            model = meta_model

    user = UserFactory()
    VerificationFactory(user=user, is_verified=True)

    upload = UserUploadFactory(
        creator=user,
    )
    upload.status = UserUpload.StatusChoices.COMPLETED
    upload.save()

    # Sanity: attempt to create object without doubly
    # assigned upload
    form1 = TestForm(
        user=user,
        data={
            "creator": user,
            "user_upload": upload.pk,
        },
    )
    assert form1.is_valid(), form1.errors

    # Create a component-image object that uses
    # the upload
    factory(user_upload=upload)

    form2 = TestForm(
        user=user,
        data={
            "creator": user,
            "user_upload": upload.pk,
        },
    )
    assert not form2.is_valid(), "Form should not be valid"
    assert "user_upload" in form2.errors, "Errors should be about user_upload"
    assert "The selected upload is already used" in str(
        form2.errors["user_upload"]
    )
