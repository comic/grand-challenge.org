from urllib.parse import urlencode

import pytest
from django.core.exceptions import ValidationError
from django.http import QueryDict
from guardian.shortcuts import assign_perm

from grandchallenge.cases.form_fields import (
    DICOMUploadField,
    ImageSourceChoiceField,
    ImageSourceChoices,
)
from grandchallenge.cases.widgets import (
    DICOMUploadWidgetSuffixes,
    DICOMUploadWithName,
    FlexibleImageField,
)
from grandchallenge.components.forms import (
    INTERFACE_FORM_FIELD_PREFIX,
    FlexibleWidgetPrefixes,
    InterfaceFormFieldsMixin,
)
from grandchallenge.components.models import ComponentInterface, SourceChoices
from grandchallenge.uploads.models import UserUpload
from tests.cases_tests.factories import DICOMImageSetFactory
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
    prefixed_interface_slug = f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}"
    field = FlexibleImageField(user=user, interface=ci)

    parsed_value_for_empty_data = field.widget.value_from_datadict(
        data=QueryDict(""), name=prefixed_interface_slug, files={}
    )
    decompressed_value_for_missing_value = field.widget.decompress(value=None)

    assert (
        parsed_value_for_empty_data
        == decompressed_value_for_missing_value
        == [None, None]
    )
    with pytest.raises(ValidationError):
        field.clean(parsed_value_for_empty_data)

    parsed_value_no_selected_data = field.widget.value_from_datadict(
        data=QueryDict(urlencode({prefixed_interface_slug: ""})),
        name=prefixed_interface_slug,
        files={},
    )
    decompressed_value_for_no_selected_data = field.widget.decompress(
        value=[""]
    )

    assert (
        parsed_value_no_selected_data
        == decompressed_value_for_no_selected_data
        == [None, None]
    )
    with pytest.raises(ValidationError):
        field.clean(parsed_value_no_selected_data)

    parsed_value_for_image_with_permission = field.widget.value_from_datadict(
        data=QueryDict(urlencode({prefixed_interface_slug: im1.pk})),
        name=prefixed_interface_slug,
        files={},
    )
    decompressed_value_for_image_with_permission = field.widget.decompress(
        [im1.pk]
    )

    assert (
        parsed_value_for_image_with_permission
        == decompressed_value_for_image_with_permission
        == [str(im1.pk), None]
    )
    assert field.clean(parsed_value_for_image_with_permission) == im1

    parsed_value_for_image_without_permission = (
        field.widget.value_from_datadict(
            data=QueryDict(urlencode({prefixed_interface_slug: im2.pk})),
            name=prefixed_interface_slug,
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
        datadict.appendlist(prefixed_interface_slug, str(id))
    parsed_value_for_upload_from_user = field.widget.value_from_datadict(
        data=datadict,
        name=prefixed_interface_slug,
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
            data=QueryDict(urlencode({prefixed_interface_slug: upload3.pk})),
            name=prefixed_interface_slug,
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
        data=QueryDict(urlencode({prefixed_interface_slug: "IMAGE_UPLOAD"})),
        name=prefixed_interface_slug,
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
def test_image_search_validates_image_dicom_kind():
    user = UserFactory()
    image_panimg = ImageFactory()
    image_dicom = ImageFactory(dicom_image_set=DICOMImageSetFactory())
    assign_perm("cases.view_image", user, image_panimg)
    assign_perm("cases.view_image", user, image_dicom)
    ci_panimg = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.PANIMG_IMAGE
    )
    ci_dicom = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.DICOM_IMAGE_SET
    )
    field_panimg = FlexibleImageField(user=user, interface=ci_panimg)
    field_dicom = FlexibleImageField(user=user, interface=ci_dicom)

    assert field_panimg.clean([str(image_panimg.pk), None]) == image_panimg
    with pytest.raises(ValidationError):
        field_panimg.clean([str(image_dicom.pk), None])
    assert field_dicom.clean([str(image_dicom.pk), None]) == image_dicom
    with pytest.raises(ValidationError):
        field_dicom.clean([str(image_panimg.pk), None])


@pytest.mark.django_db
def test_flexible_image_widget_prepopulated_value():
    user_with_perm, user_without_perm = UserFactory.create_batch(2)
    im = ImageFactory(name="test_image")
    assign_perm("cases.view_image", user_with_perm, im)
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.PANIMG_IMAGE)
    civ = ComponentInterfaceValueFactory(interface=ci, image=im)

    field = FlexibleImageField(user=user_with_perm, interface=ci, initial=civ)
    assert field.widget.attrs["current_value"] == [civ.image]
    assert field.initial == civ.image.pk

    field = FlexibleImageField(
        user=user_with_perm, interface=ci, initial=civ.image.pk
    )
    assert field.widget.attrs["current_value"] == [civ.image]
    assert field.initial == civ.image.pk

    field = FlexibleImageField(
        user=user_without_perm, interface=ci, initial=civ
    )
    assert field.widget.attrs["current_value"] is None
    assert field.initial is None

    field = FlexibleImageField(
        user=user_without_perm, interface=ci, initial=civ.image.pk
    )
    assert field.widget.attrs["current_value"] is None
    assert field.initial is None


@pytest.mark.django_db
def test_image_upload_field_validation():
    user = UserFactory()
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.PANIMG_IMAGE)
    field = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci, user=user
    )[f"{FlexibleWidgetPrefixes.UPLOAD}{ci.slug}"]

    # Normal case: two uploads from the user with completed status
    upload1, upload2 = UserUploadFactory.create_batch(
        2,
        creator=user,
    )
    upload1.status = UserUpload.StatusChoices.COMPLETED
    upload1.save()
    upload2.status = UserUpload.StatusChoices.COMPLETED
    upload2.save()
    data = [str(upload1.pk), str(upload2.pk)]
    cleaned_data = field.clean(data)

    assert cleaned_data.count() == 2
    assert upload1 in cleaned_data.all()
    assert upload2 in cleaned_data.all()

    # Upload from another user
    other_user_upload = UserUploadFactory(
        creator=UserFactory(),
    )
    other_user_upload.status = UserUpload.StatusChoices.COMPLETED
    other_user_upload.save()
    data_from_other_user = [str(other_user_upload.pk)]
    with pytest.raises(ValidationError):
        field.clean(data_from_other_user)

    # Upload with non-completed status
    non_completed_upload = UserUploadFactory(
        creator=user,
    )
    assert non_completed_upload.status != UserUpload.StatusChoices.COMPLETED
    data_from_non_completed_upload = [str(non_completed_upload.pk)]
    with pytest.raises(ValidationError):
        field.clean(data_from_non_completed_upload)


@pytest.mark.django_db
def test_dicom_upload_field_validation():
    user = UserFactory()
    ci = ComponentInterfaceFactory()
    prefixed_interface_slug = f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}"
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
            f"{prefixed_interface_slug}_{DICOMUploadWidgetSuffixes.UPLOADS}": [
                str(upload1.pk)
            ],
            f"{prefixed_interface_slug}_{DICOMUploadWidgetSuffixes.NAME}": "test_image",
        },
        name=f"{prefixed_interface_slug}",
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
            f"{prefixed_interface_slug}_{DICOMUploadWidgetSuffixes.UPLOADS}": [
                str(upload2.pk)
            ],
            f"{prefixed_interface_slug}_{DICOMUploadWidgetSuffixes.NAME}": "test_image_2",
        },
        name=f"{prefixed_interface_slug}",
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
def test_image_source_select_prepopulated_value():
    im = ImageFactory(
        name="test_image",
        dicom_image_set=DICOMImageSetFactory(),
    )
    ci = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.DICOM_IMAGE_SET
    )
    civ = ComponentInterfaceValueFactory(interface=ci, image=im)

    field = ImageSourceChoiceField(current_socket_value=civ)

    assert field.current_socket_value == civ
    assert field.choices == [
        ("CURRENT", "test_image"),
        ("SEARCH", "Select an existing image"),
        ("UPLOAD", "Upload a new image"),
    ]
    assert field.clean(SourceChoices.CURRENT.value) == im
    with pytest.raises(ValidationError, match="This field is required."):
        field.clean(ImageSourceChoices.UNDEFINED.value)

    field = ImageSourceChoiceField()

    assert field.choices == [
        ("", "Choose data source..."),
        ("SEARCH", "Select an existing image"),
        ("UPLOAD", "Upload a new image"),
    ]
    assert field.current_socket_value is None
    with pytest.raises(ValidationError, match="Select a valid choice."):
        field.clean(SourceChoices.CURRENT.value)
    with pytest.raises(ValidationError, match="This field is required."):
        field.clean(ImageSourceChoices.UNDEFINED.value)
