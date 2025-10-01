from urllib.parse import urlencode

import pytest
from django.core.exceptions import ValidationError
from django.http import QueryDict
from guardian.shortcuts import assign_perm

from grandchallenge.cases.widgets import (
    DICOMUploadField,
    DICOMUploadWidgetSuffixes,
    DICOMUploadWithName,
    FlexibleImageField,
)
from grandchallenge.components.form_fields import (
    INTERFACE_FORM_FIELD_PREFIX,
    InterfaceFormFieldFactory,
)
from grandchallenge.components.models import ComponentInterface
from grandchallenge.uploads.models import UserUpload
from tests.cases_tests.factories import (
    DICOMImageSetFactory,
    DICOMImageSetUploadFactory,
)
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
    upload2 = UserUploadFactory(creator=user)
    upload2.status = UserUpload.StatusChoices.COMPLETED
    upload2.save()
    upload3 = UserUploadFactory()
    upload3.status = UserUpload.StatusChoices.COMPLETED
    upload3.save()
    im1, im2 = ImageFactory.create_batch(2)
    assign_perm("cases.view_image", user, im1)
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.PANIMG_IMAGE)
    field = FlexibleImageField(user=user)
    parsed_value_for_empty_data = field.widget.value_from_datadict(
        data=QueryDict(""), name=ci.slug, files={}
    )
    decompressed_value_for_missing_value = field.widget.decompress(value=None)
    assert parsed_value_for_empty_data == [None, None]
    assert decompressed_value_for_missing_value == [None, None]

    parsed_value_for_image_with_permission = field.widget.value_from_datadict(
        data=QueryDict(urlencode({ci.slug: im1.pk})), name=ci.slug, files={}
    )
    decompressed_value_for_image_with_permission = field.widget.decompress(
        [im1.pk]
    )

    assert (
        parsed_value_for_image_with_permission
        == decompressed_value_for_image_with_permission
        == [
            str(im1.pk),
            None,
        ]
    )
    assert field.clean(parsed_value_for_image_with_permission) == im1

    parsed_value_for_image_without_permission = (
        field.widget.value_from_datadict(
            data=QueryDict(urlencode({ci.slug: im2.pk})),
            name=ci.slug,
            files={},
        )
    )
    decompressed_value_for_image_without_permission = field.widget.decompress(
        [im2.pk]
    )
    assert (
        parsed_value_for_image_without_permission
        == decompressed_value_for_image_without_permission
        == [str(im2.pk), None]
    )
    with pytest.raises(ValidationError):
        field.clean(parsed_value_for_image_without_permission)

    datadict = QueryDict(mutable=True)
    for id in [upload1.pk, upload2.pk]:
        datadict.appendlist(ci.slug, str(id))
    parsed_value_for_upload_from_user = field.widget.value_from_datadict(
        data=datadict,
        name=ci.slug,
        files={},
    )
    decompressed_value_for_upload_from_user = field.widget.decompress(
        [str(upload1.pk), str(upload2.pk)]
    )
    assert (
        parsed_value_for_upload_from_user
        == decompressed_value_for_upload_from_user
        == [None, [str(upload1.pk), str(upload2.pk)]]
    )
    assert field.clean(parsed_value_for_upload_from_user).count() == 2
    assert upload1 in field.clean(parsed_value_for_upload_from_user).all()
    assert upload2 in field.clean(parsed_value_for_upload_from_user).all()

    parsed_value_from_upload_from_other_user = (
        field.widget.value_from_datadict(
            data=QueryDict(urlencode({ci.slug: upload3.pk})),
            name=ci.slug,
            files={},
        )
    )
    decompressed_value_for_upload_from_other_user = field.widget.decompress(
        [str(upload3.pk)]
    )
    assert (
        parsed_value_from_upload_from_other_user
        == decompressed_value_for_upload_from_other_user
        == [None, [str(upload3.pk)]]
    )
    with pytest.raises(ValidationError):
        field.clean(parsed_value_from_upload_from_other_user)

    parsed_value_for_missing_value = field.widget.value_from_datadict(
        data=QueryDict(urlencode({ci.slug: "IMAGE_UPLOAD"})),
        name=ci.slug,
        files={},
    )
    decompressed_value_for_missing_value = field.widget.decompress(
        ["IMAGE_UPLOAD"]
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
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.PANIMG_IMAGE)
    civ = ComponentInterfaceValueFactory(interface=ci, image=im)

    field = InterfaceFormFieldFactory(
        interface=ci, user=user_with_perm, initial=civ
    )
    assert field.widget.attrs["current_value"] == [civ.image]
    assert field.initial == civ.image.pk

    field = InterfaceFormFieldFactory(
        interface=ci, user=user_with_perm, initial=civ.image.pk
    )
    assert field.widget.attrs["current_value"] == [civ.image]
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


@pytest.mark.django_db
def test_dicom_upload_field_validation():
    user = UserFactory()
    ci = ComponentInterfaceFactory()
    field = DICOMUploadField(user=user)
    upload1 = UserUploadFactory(creator=user)
    upload1.status = UserUpload.StatusChoices.COMPLETED
    upload1.save()
    upload2 = UserUploadFactory()
    upload2.status = UserUpload.StatusChoices.COMPLETED
    upload2.save()

    dicom_upload = DICOMUploadWithName(
        name="test_image",
        user_uploads=[str(upload1.pk)],
    )
    parsed_value_for_upload_from_user = field.widget.value_from_datadict(
        data={
            f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}_{DICOMUploadWidgetSuffixes[1]}": [
                str(upload1.pk)
            ],
            f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}_{DICOMUploadWidgetSuffixes[0]}": "test_image",
        },
        name=f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}",
        files={},
    )
    decompressed_value_for_upload_from_user = field.widget.decompress(
        dicom_upload
    )
    assert (
        parsed_value_for_upload_from_user
        == decompressed_value_for_upload_from_user
        == ["test_image", [str(upload1.pk)]]
    )
    assert field.clean(parsed_value_for_upload_from_user) == dicom_upload

    dicom_upload_2 = DICOMUploadWithName(
        name="test_image_2",
        user_uploads=[str(upload2.pk)],
    )
    parsed_value_from_upload_from_other_user = field.widget.value_from_datadict(
        data={
            f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}_{DICOMUploadWidgetSuffixes[1]}": [
                str(upload2.pk)
            ],
            f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}_{DICOMUploadWidgetSuffixes[0]}": "test_image_2",
        },
        name=f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}",
        files={},
    )
    decompressed_value_for_upload_from_other_user = field.widget.decompress(
        dicom_upload_2
    )
    assert (
        parsed_value_from_upload_from_other_user
        == decompressed_value_for_upload_from_other_user
        == ["test_image_2", [str(upload2.pk)]]
    )
    with pytest.raises(ValidationError):
        field.clean(parsed_value_from_upload_from_other_user)


@pytest.mark.django_db
def test_dicom_upload_widget_prepopulated_value(mocker):
    user_with_perm, user_without_perm = UserFactory.create_batch(2)
    upload = DICOMImageSetUploadFactory()
    upload.user_uploads.set([UserUploadFactory(creator=user_with_perm)])
    im = ImageFactory(
        name="test_image",
        dicom_image_set=DICOMImageSetFactory(dicom_image_set_upload=upload),
    )
    assign_perm("cases.view_image", user_with_perm, im)
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.PANIMG_IMAGE)
    civ = ComponentInterfaceValueFactory(interface=ci, image=im)

    # fake DICOM ci for now
    # TODO: create a proper DICOM super kind ci above
    mocker.patch(
        "grandchallenge.components.models.ComponentInterface.is_dicom_image_kind",
        return_value=True,
    )

    field = InterfaceFormFieldFactory(
        interface=ci, user=user_with_perm, initial=civ
    )
    assert field.widget.attrs["current_value"] == civ.image
    assert field.initial.name == civ.image.name
    assert field.initial.user_uploads == [
        str(upload.pk)
        for upload in civ.image.dicom_image_set.dicom_image_set_upload.user_uploads.all()
    ]

    field = InterfaceFormFieldFactory(
        interface=ci, user=user_without_perm, initial=civ
    )
    assert field.widget.attrs["current_value"] is None
    assert field.initial is None
