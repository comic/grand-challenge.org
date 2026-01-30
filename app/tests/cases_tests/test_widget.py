import pytest
from django.core.exceptions import ValidationError

from grandchallenge.cases.form_fields import (
    DICOMUploadField,
    ImageSourceChoiceField,
    ImageSourceChoices,
)
from grandchallenge.cases.widgets import (
    DICOMUploadWidgetSuffixes,
    DICOMUploadWithName,
)
from grandchallenge.components.form_fields import SourceChoices
from grandchallenge.components.forms import (
    INTERFACE_FORM_FIELD_PREFIX,
    FlexibleWidgetPrefixes,
    InterfaceFormFieldsMixin,
)
from grandchallenge.components.models import ComponentInterface
from grandchallenge.uploads.models import UserUpload
from tests.cases_tests.factories import DICOMImageSetFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory
from tests.uploads_tests.factories import UserUploadFactory


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
