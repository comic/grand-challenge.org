import gzip
import json
import uuid
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import factory
import pytest
from botocore.stub import Stubber
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.core.files import File

from grandchallenge.cases.models import (
    DICOMImageSet,
    Image,
    JobSummary,
    generate_dicom_id_suffix,
)
from tests.cases_tests.factories import (
    DICOMImageSetFactory,
    DICOMImageSetUploadFactory,
    ImageFactory,
    ImageFactoryWithImageFile,
    ImageFactoryWithImageFile4D,
    ImageFileFactoryWithMHDFile,
    ImageFileFactoryWithRAWFile,
    fake_image_frame_id,
)
from tests.factories import ImageFileFactory
from tests.uploads_tests.factories import UserUploadFactory


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
        "arn:aws:iam::123456789012:role/health-imaging-import-job-access"
    )
    di_upload = DICOMImageSetUploadFactory()

    with Stubber(di_upload._health_imaging_client) as s:
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


@pytest.fixture
def import_job_summary():
    def _import_job_summary(*, di_upload, **kwargs):
        job_summary_data = {
            "jobId": "381d850256f30b24358c0a3d9e389670",
            "datastoreId": "bbc4f3cccbae4095a34170fddc19b13d",
            "inputS3Uri": f"s3://healthimaging/inputs/{di_upload.pk}/",
            "outputS3Uri": "s3://healthimaging/logs/bbc4f3cccbae4095a34170fddc19b13d-DicomImport-3d8e036cc21a83e10bbb98c9d29258a5/",
            "successOutputS3Uri": "s3://healthimaging/logs/bbc4f3cccbae4095a34170fddc19b13d-DicomImport-3d8e036cc21a83e10bbb98c9d29258a5/SUCCESS/",
            "failureOutputS3Uri": "s3://healthimaging/logs/bbc4f3cccbae4095a34170fddc19b13d-DicomImport-3d8e036cc21a83e10bbb98c9d29258a5/FAILURE/",
            "numberOfScannedFiles": 1,
            "numberOfImportedFiles": 1,
            "numberOfFilesWithCustomerError": 0,
            "numberOfFilesWithServerError": 0,
            "numberOfGeneratedImageSets": 1,
            "imageSetsSummary": [
                {
                    "imageSetId": "e616d1f717da6f80fed6271ad184b7f0",
                    "imageSetVersion": 1,
                    "isPrimary": True,
                    "numberOfMatchedSOPInstances": 1,
                }
            ],
        }
        job_summary_data.update(kwargs)
        return JobSummary(**job_summary_data)

    return _import_job_summary


@pytest.mark.django_db
def test_handle_failed_job(mocker, import_job_summary):
    di_upload = DICOMImageSetUploadFactory()
    job_summary = import_job_summary(
        di_upload=di_upload,
        **{
            "numberOfScannedFiles": 1,
            "numberOfImportedFiles": 0,
            "numberOfFilesWithCustomerError": 0,
            "numberOfFilesWithServerError": 1,
            "numberOfGeneratedImageSets": 0,
            "imageSetsSummary": [],
        },
    )
    failure_log = [
        {
            "inputFile": f"inputs/{di_upload.pk}/",
            "exception": {
                "exceptionType": "SomeException",
                "message": "The import job failed.",
            },
        }
    ]
    mock_get_failure_log = mocker.patch.object(
        di_upload, "get_job_output_failure_log", return_value=failure_log
    )
    spy_delete_image_sets = mocker.spy(di_upload, "delete_image_sets")

    with pytest.raises(RuntimeError) as error:
        di_upload.handle_failed_job(job_summary=job_summary)

    assert (
        str(error.value)
        == f"Import job {job_summary.job_id} failed for DICOMImageSetUpload {di_upload.pk}"
    )

    mock_get_failure_log.assert_called_once_with(job_summary=job_summary)
    spy_delete_image_sets.assert_called_once_with(job_summary=job_summary)
    assert di_upload.internal_failure_log == failure_log


@pytest.mark.django_db
def test_validate_image_set_no_generated_image_set(mocker, import_job_summary):
    di_upload = DICOMImageSetUploadFactory()
    job_summary = import_job_summary(
        di_upload=di_upload,
        **{
            "numberOfScannedFiles": 1,
            "numberOfImportedFiles": 0,
            "numberOfFilesWithCustomerError": 1,
            "numberOfFilesWithServerError": 0,
            "numberOfGeneratedImageSets": 0,
            "imageSetsSummary": [],
        },
    )
    mocker.patch.object(di_upload, "get_job_summary", return_value=job_summary)
    mock_get_failure_log = mocker.patch.object(
        di_upload, "get_job_output_failure_log"
    )

    with pytest.raises(RuntimeError) as error:
        di_upload.validate_image_set(job_summary=job_summary)

    assert (
        str(error.value)
        == f"Import job {job_summary.job_id} failed for DICOMImageSetUpload {di_upload.pk}"
    )

    mock_get_failure_log.assert_called_once_with(job_summary=job_summary)


@pytest.mark.django_db
def test_validate_image_set_multiple_generated_image_sets(
    mocker,
    django_capture_on_commit_callbacks,
    import_job_summary,
):
    di_upload = DICOMImageSetUploadFactory()
    image_set_id_1 = "e616d1f717da6f80fed6271ad184b7f0"
    image_set_id_2 = "381d850256f30b24358c0a3d9e389670"
    job_summary = import_job_summary(
        di_upload=di_upload,
        **{
            "numberOfScannedFiles": 2,
            "numberOfImportedFiles": 2,
            "numberOfFilesWithCustomerError": 0,
            "numberOfFilesWithServerError": 0,
            "numberOfGeneratedImageSets": 2,
            "imageSetsSummary": [
                {
                    "imageSetId": image_set_id_1,
                    "imageSetVersion": 1,
                    "isPrimary": True,
                    "numberOfMatchedSOPInstances": 1,
                },
                {
                    "imageSetId": image_set_id_2,
                    "imageSetVersion": 1,
                    "isPrimary": True,
                    "numberOfMatchedSOPInstances": 1,
                },
            ],
        },
    )
    mocker.patch.object(di_upload, "get_job_summary", return_value=job_summary)
    mock_signature = MagicMock()
    mock_signature.apply_async = MagicMock()
    mock_delete_image_set_task = mocker.patch(
        "grandchallenge.cases.tasks.delete_health_imaging_image_set.signature",
        return_value=mock_signature,
    )

    with (
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(RuntimeError) as error,
    ):
        di_upload.validate_image_set(job_summary=job_summary)

    assert (
        str(error.value) == "Multiple image sets created. Expected only one."
    )

    assert mock_delete_image_set_task.call_count == 2
    mock_delete_image_set_task.assert_any_call(
        kwargs={"image_set_id": image_set_id_1}
    )
    mock_delete_image_set_task.assert_any_call(
        kwargs={"image_set_id": image_set_id_2}
    )
    assert mock_signature.apply_async.call_count == 2


@pytest.mark.django_db
def test_validate_image_set_generated_image_set_not_primary(
    mocker,
    django_capture_on_commit_callbacks,
    import_job_summary,
):
    di_upload = DICOMImageSetUploadFactory()
    image_set_id = "e616d1f717da6f80fed6271ad184b7f0"
    job_summary = import_job_summary(
        di_upload=di_upload,
        **{
            "imageSetsSummary": [
                {
                    "imageSetId": image_set_id,
                    "imageSetVersion": 1,
                    "isPrimary": False,
                    "numberOfMatchedSOPInstances": 1,
                },
            ],
        },
    )
    mocker.patch.object(di_upload, "get_job_summary", return_value=job_summary)
    mock_signature = MagicMock()
    mock_signature.apply_async = MagicMock()
    mock_delete_image_set_task = mocker.patch(
        "grandchallenge.cases.tasks.delete_health_imaging_image_set.signature",
        return_value=mock_signature,
    )

    with (
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(RuntimeError) as error,
    ):
        di_upload.validate_image_set(job_summary=job_summary)

    assert (
        str(error.value)
        == "New instance is not primary: metadata conflicts with already existing instance."
    )

    mock_delete_image_set_task.assert_called_once_with(
        kwargs={"image_set_id": image_set_id}
    )
    assert mock_signature.apply_async.call_count == 1


@pytest.mark.django_db
def test_validate_image_set_generated_image_set_not_first_version(
    mocker,
    django_capture_on_commit_callbacks,
    import_job_summary,
):
    di_upload = DICOMImageSetUploadFactory()
    image_set_id = "e616d1f717da6f80fed6271ad184b7f0"
    job_summary = import_job_summary(
        di_upload=di_upload,
        **{
            "imageSetsSummary": [
                {
                    "imageSetId": image_set_id,
                    "imageSetVersion": 2,
                    "isPrimary": True,
                    "numberOfMatchedSOPInstances": 1,
                },
            ],
        },
    )
    mocker.patch.object(di_upload, "get_job_summary", return_value=job_summary)
    mock_signature = MagicMock()
    mock_signature.apply_async = MagicMock()
    mock_revert_image_set_to_initial_version = mocker.patch(
        "grandchallenge.cases.tasks.revert_image_set_to_initial_version.signature",
        return_value=mock_signature,
    )

    with (
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(RuntimeError) as error,
    ):
        di_upload.validate_image_set(job_summary=job_summary)

    assert (
        str(error.value)
        == "Instance already exists. This should never happen!"
    )

    mock_revert_image_set_to_initial_version.assert_called_once_with(
        kwargs={"image_set_id": image_set_id, "version_id": 2}
    )
    assert mock_signature.apply_async.call_count == 1


@pytest.mark.django_db
def test_handle_completed_job_generated_image_set(mocker, import_job_summary):
    di_upload = DICOMImageSetUploadFactory()
    job_summary = import_job_summary(di_upload=di_upload)
    mocker.patch.object(di_upload, "get_job_summary", return_value=job_summary)
    mock_convert_image_set_to_internal = mocker.patch.object(
        di_upload, "convert_image_set_to_internal"
    )

    di_upload.handle_completed_job(job_summary=job_summary)

    mock_convert_image_set_to_internal.assert_called_once_with(
        image_set_id=job_summary.image_sets_summary[0].image_set_id,
    )


@pytest.mark.django_db
def test_instance_uuid_generation():
    di_upload = DICOMImageSetUploadFactory()

    assert di_upload.study_instance_uid == generate_dicom_id_suffix(
        pk=di_upload.pk, suffix_type="study"
    )
    assert di_upload.series_instance_uid == generate_dicom_id_suffix(
        pk=di_upload.pk, suffix_type="series"
    )


@pytest.mark.django_db
def test_deidentify_user_uploads_idempotency(mocker, settings):
    settings.AWS_HEALTH_IMAGING_BUCKET_NAME = "test-bucket"
    di_upload = DICOMImageSetUploadFactory()
    mock_deidentify_files = mocker.patch.object(di_upload, "_deidentify_files")

    with Stubber(di_upload._s3_client) as s:
        s.add_response(
            method="head_object",
            service_response={},  # response indicating there already is a marker file
            expected_params={
                "Bucket": settings.AWS_HEALTH_IMAGING_BUCKET_NAME,
                "Key": di_upload._marker_file_key,
            },
        )
        di_upload.deidentify_user_uploads()

    mock_deidentify_files.assert_not_called()


@pytest.mark.django_db
def test_deidentify_user_uploads(mocker, settings):
    settings.AWS_HEALTH_IMAGING_BUCKET_NAME = "test-bucket"
    di_upload = DICOMImageSetUploadFactory()
    mock_deidentify_files = mocker.patch.object(di_upload, "_deidentify_files")

    mock_qs = mocker.MagicMock()
    mocker.patch.object(
        type(di_upload.user_uploads), "all", return_value=mock_qs
    )

    with Stubber(di_upload._s3_client) as s:
        s.add_client_error(
            method="head_object",
            service_error_code="404",
            service_message="Not Found",
            expected_params={
                "Bucket": settings.AWS_HEALTH_IMAGING_BUCKET_NAME,
                "Key": di_upload._marker_file_key,
            },
        )
        s.add_response(
            method="put_object",
            expected_params={
                "Bucket": settings.AWS_HEALTH_IMAGING_BUCKET_NAME,
                "Key": di_upload._marker_file_key,
                "Body": b"",
            },
            service_response={},
        )
        di_upload.deidentify_user_uploads()

    mock_deidentify_files.assert_called_once()
    mock_qs.delete.assert_called_once()


@pytest.mark.django_db
def test_deidentify_files_processes_all_user_uploads(mocker):
    di_upload = DICOMImageSetUploadFactory()
    uploads = UserUploadFactory.create_batch(3)
    di_upload.user_uploads.set(uploads)

    mock_download = mocker.patch.object(
        type(di_upload._s3_client), "download_fileobj"
    )
    mock_upload = mocker.patch.object(
        type(di_upload._s3_client), "upload_fileobj"
    )
    mock_deid = mocker.patch("grandchallenge.cases.models.DicomDeidentifier")
    mock_instance = mock_deid.return_value

    di_upload._deidentify_files()

    mock_deid.assert_called_once_with(
        study_instance_uid_suffix=di_upload.study_instance_uid,
        series_instance_uid_suffix=di_upload.series_instance_uid,
        assert_unique_value_for=[
            "StudyInstanceUID",
            "SeriesInstanceUID",
            "PatientID",
            "StudyID",
            "StudyDate",
            "AccessionNumber",
            "SeriesNumber",
        ],
    )
    assert mock_download.call_count == len(uploads)
    assert mock_upload.call_count == len(uploads)
    assert mock_instance.deidentify_file.call_count == len(uploads)


@pytest.mark.django_db
def test_delete_dicom_image_set_post_delete_image():
    dicom_image_set = DICOMImageSetFactory()
    image = ImageFactory(dicom_image_set=dicom_image_set)

    assert DICOMImageSet.objects.count() != 0

    image.delete()

    assert DICOMImageSet.objects.count() == 0


@pytest.mark.django_db
def test_delete_health_imaging_image_set_post_delete_dicom_image_set(
    django_capture_on_commit_callbacks,
    mocker,
):
    dicom_image_set = DICOMImageSetFactory()
    mock_signature = MagicMock()
    mock_signature.apply_async = MagicMock()
    mock_delete_health_imaging_image_set = mocker.patch(
        "grandchallenge.cases.tasks.delete_health_imaging_image_set.signature",
        return_value=mock_signature,
    )

    with django_capture_on_commit_callbacks(execute=True):
        dicom_image_set.delete()

    mock_delete_health_imaging_image_set.assert_called_once_with(
        kwargs={"image_set_id": dicom_image_set.image_set_id}
    )
    assert mock_signature.apply_async.call_count == 1


@pytest.mark.django_db
def test_convert_image_set_to_internal(settings):
    settings.AWS_HEALTH_IMAGING_DATASTORE_ID = "test-datastore-id"

    dicom_image_set_upload = DICOMImageSetUploadFactory(name="foo")
    image_set_id = "e616d1f717da6f80fed6271ad184b7f0"
    image_frame_ids = [fake_image_frame_id() for _ in range(4)]

    assert Image.objects.count() == 0
    assert DICOMImageSet.objects.count() == 0

    with (
        Stubber(dicom_image_set_upload._health_imaging_client) as s,
        BytesIO() as buffer,
    ):
        content = json.dumps(
            {
                "Study": {
                    "Series": {
                        "foo": {
                            "Instances": {
                                "bar": {
                                    "ImageFrames": [
                                        {"ID": image_frame_ids[0]},
                                        {"ID": image_frame_ids[1]},
                                    ]
                                },
                                "baz": {
                                    "ImageFrames": [{"ID": image_frame_ids[2]}]
                                },
                            }
                        },
                        "foobar": {
                            "Instances": {
                                "bar": {
                                    "ImageFrames": [
                                        {"ID": image_frame_ids[3]},
                                    ]
                                },
                            }
                        },
                    }
                }
            }
        ).encode("utf-8")

        buffer.write(gzip.compress(data=content))
        buffer.seek(0)

        s.add_response(
            method="get_image_set_metadata",
            service_response={"imageSetMetadataBlob": buffer},
            expected_params={
                "datastoreId": settings.AWS_HEALTH_IMAGING_DATASTORE_ID,
                "imageSetId": image_set_id,
                "versionId": "1",
            },
        )
        dicom_image_set_upload.convert_image_set_to_internal(
            image_set_id=image_set_id,
        )

    assert Image.objects.count() == 1
    assert DICOMImageSet.objects.count() == 1

    dicom_image_set = DICOMImageSet.objects.first()

    assert dicom_image_set.image_set_id == image_set_id
    assert dicom_image_set.image_frame_ids == image_frame_ids

    image = Image.objects.first()

    assert image.dicom_image_set == dicom_image_set
    assert image.name == "foo"
