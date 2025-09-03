import uuid
from pathlib import Path

import factory
import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.core.files import File

from grandchallenge.cases.models import DICOMImageSetUploadStatusChoices
from tests.cases_tests.factories import (
    DICOMImageSetUploadFactory,
    ImageFactory,
    ImageFactoryWithImageFile,
    ImageFactoryWithImageFile4D,
    ImageFileFactoryWithMHDFile,
    ImageFileFactoryWithRAWFile,
)
from tests.factories import ImageFileFactory


@pytest.mark.django_db
def test_image_str():
    model = ImageFactory()
    assert str(model) == f"Image {model.name} {model.shape_without_color}"


@pytest.mark.django_db
class TestGetSitkImage:
    def test_multiple_mhds(self):
        extra_mhd = ImageFileFactoryWithMHDFile()
        extra_mhd_file = ImageFileFactoryWithMHDFile()
        extra_raw = ImageFileFactoryWithRAWFile()
        extra_raw_file = ImageFileFactoryWithRAWFile()
        image = ImageFactoryWithImageFile(
            files=(extra_mhd, extra_raw, extra_mhd_file, extra_raw_file)
        )
        with pytest.raises(MultipleObjectsReturned):
            _ = image.sitk_image

    def test_4d_mhd_object(self):
        image = ImageFactoryWithImageFile4D()
        assert image.sitk_image.GetDimension() == 4

    def test_no_mhd_object(self):
        image = ImageFactoryWithImageFile()
        image.files.get(file__endswith=".mhd").delete()
        with pytest.raises(FileNotFoundError):
            _ = image.sitk_image

    def test_no_raw_object(self):
        image = ImageFactoryWithImageFile()
        image.files.get(file__endswith=".zraw").delete()
        with pytest.raises(FileNotFoundError):
            _ = image.sitk_image

    def test_file_not_found_mhd(self):
        image = ImageFactoryWithImageFile()
        imagefile = image.files.get(file__endswith=".mhd")
        imagefile.file.storage.delete(imagefile.file.name)
        with pytest.raises(FileNotFoundError):
            _ = image.sitk_image

    def test_file_not_found_raw(self):
        image = ImageFactoryWithImageFile()
        imagefile = image.files.get(file__endswith=".zraw")
        imagefile.file.storage.delete(imagefile.file.name)
        with pytest.raises(FileNotFoundError):
            _ = image.sitk_image

    def test_file_too_large_throws_error(self, tmpdir):
        image = ImageFactoryWithImageFile()

        # Remove zraw file
        old_raw = image.files.get(file__endswith=".zraw")
        raw_file_name = Path(old_raw.file.name).name
        old_raw.delete()

        # Create fake too large zraw file
        too_large_file_raw = tmpdir.join(raw_file_name)
        f = too_large_file_raw.open(mode="wb")
        f.seek(settings.MAX_SITK_FILE_SIZE)
        f.write(b"\0")
        f.close()

        # Add too large file as ImageFile model to image.files
        too_large_file_field = factory.django.FileField(
            from_path=str(too_large_file_raw)
        )
        too_large_imagefile = ImageFileFactory(file=too_large_file_field)
        image.files.add(too_large_imagefile)

        # Try to open and catch expected exception
        with pytest.raises(IOError) as exec_info:
            _ = image.sitk_image
        assert "File exceeds maximum file size." in str(
            exec_info.value.args[0]
        )

    def test_correct_dimensions(self):
        image = ImageFactoryWithImageFile()
        sitk_image = image.sitk_image
        assert sitk_image.GetDimension() == 2
        assert sitk_image.GetSize() == (3, 4)
        assert sitk_image.GetOrigin() == (0.0, 0.0)
        assert sitk_image.GetSpacing() == (1.0, 1.0)
        assert sitk_image.GetNumberOfComponentsPerPixel() == 3
        assert sitk_image.GetPixelIDValue() == 13
        assert (
            sitk_image.GetPixelIDTypeAsString()
            == "vector of 8-bit unsigned integer"
        )


@pytest.mark.django_db
def test_image_file_cleanup(uploaded_image):
    filename = f"{uuid.uuid4()}.zraw"

    i = ImageFactory()
    f = ImageFileFactory(image=i, file=None)
    f.file.save(filename, File(uploaded_image()))

    storage = f.file.storage
    filepath = f.file.name

    assert storage.exists(name=filepath)

    i.delete()

    assert not storage.exists(name=filepath)


def test_directory_file_destination():
    image = ImageFactory.build(pk="34d4df58-03eb-4bf8-a424-713e601e694e")

    file = ImageFileFactory.build(
        pk="4c572c72-1f76-44fa-b2a4-019e822eeb3f",
        image=image,
        directory=Path(__file__).parent,
    )
    assert (
        file._directory_file_destination(file=Path(__file__))
        == "images/34/d4/34d4df58-03eb-4bf8-a424-713e601e694e/4c572c72-1f76-44fa-b2a4-019e822eeb3f/cases_tests/test_models.py"
    )

    file = ImageFileFactory.build(
        pk="4c572c72-1f76-44fa-b2a4-019e822eeb3f",
        image=image,
        directory=Path(__file__).parent.parent,
    )
    assert (
        file._directory_file_destination(file=Path(__file__))
        == "images/34/d4/34d4df58-03eb-4bf8-a424-713e601e694e/4c572c72-1f76-44fa-b2a4-019e822eeb3f/tests/cases_tests/test_models.py"
    )


@pytest.mark.django_db
def test_dicomimagesetupload_import_properties():
    di_upload = DICOMImageSetUploadFactory()

    assert (
        di_upload._import_job_name
        == f"{settings.COMPONENTS_REGISTRY_PREFIX}-{di_upload.pk}"
    )
    assert (
        di_upload._import_input_s3_uri
        == f"s3://{settings.AWS_HEALTH_IMAGING_BUCKET_NAME}/inputs/{di_upload.pk}"
    )
    assert (
        di_upload._import_output_s3_uri
        == f"s3://{settings.AWS_HEALTH_IMAGING_BUCKET_NAME}/logs/{di_upload.pk}"
    )


@pytest.mark.django_db
def test_start_dicom_import_job(settings):
    settings.AWS_HEALTH_IMAGING_DATASTORE_ID = (
        "efd11ef2121b451d934757a4d14b182c"
    )
    settings.AWS_HEALTH_IMAGING_IMPORT_ROLE_ARN = (
        "arn:aws:iam::123456789012:role/healthimaging-importjob-access"
    )
    di_upload = DICOMImageSetUploadFactory()

    with Stubber(
        di_upload._health_imaging_wrapper._health_imaging_client
    ) as s:
        s.add_response(
            method="start_dicom_import_job",
            service_response={
                "datastoreId": settings.AWS_HEALTH_IMAGING_DATASTORE_ID,
                "jobId": "1234",
                "jobStatus": "SUBMITTED",
                "submittedAt": "2025-08-27T12:00:00Z",
            },
            expected_params={
                "datastoreId": settings.AWS_HEALTH_IMAGING_DATASTORE_ID,
                "inputS3Uri": di_upload._import_input_s3_uri,
                "outputS3Uri": di_upload._import_output_s3_uri,
                "dataAccessRoleArn": settings.AWS_HEALTH_IMAGING_IMPORT_ROLE_ARN,
                "jobName": di_upload._import_job_name,
            },
        )
        response = di_upload.start_dicom_import_job()

    assert response["jobStatus"] == "SUBMITTED"


@pytest.mark.django_db
def test_error_in_start_dicom_import_job(mocker):
    di_upload = DICOMImageSetUploadFactory()
    fake_client = mocker.Mock()
    fake_client.start_dicom_import_job.side_effect = ClientError(
        error_response={
            "Error": {"Code": "ValidationError", "Message": "Foo"}
        },
        operation_name="StartDICOMImportJob",
    )
    mocker.patch(
        "grandchallenge.cases.models.boto3.client", return_value=fake_client
    )

    di_upload.start_dicom_import_job()

    assert di_upload.status == DICOMImageSetUploadStatusChoices.FAILED
    assert di_upload.error_message == "An unexpected error occurred"
