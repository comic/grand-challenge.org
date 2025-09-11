import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import factory
import pytest
from botocore.stub import Stubber
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.core.files import File

from grandchallenge.cases.exceptions import (
    DICOMImportJobFailedError,
    DICOMImportJobValidationError,
)
from grandchallenge.cases.models import DICOMImageSet, Image
from tests.cases_tests.factories import (
    DICOMImageSetFactory,
    DICOMImageSetUploadFactory,
    ImageFactory,
    ImageFactoryWithImageFile,
    ImageFactoryWithImageFile4D,
    ImageFileFactoryWithMHDFile,
    ImageFileFactoryWithRAWFile,
)
from tests.factories import ImageFileFactory, ImagingModalityFactory


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
def import_job_event():
    def _import_job_event(*, di_upload, status="COMPLETED"):
        return {
            "imagingVersion": "1.0",
            "datastoreId": "bbc4f3cccbae4095a34170fddc19b13d",
            "jobName": f"gc.localhost-{di_upload.pk}",
            "jobId": "3d8e036cc21a83e10bbb98c9d29258a5",
            "jobStatus": status,
            "inputS3Uri": f"s3://healthimaging/inputs/{di_upload.pk}/",
            "outputS3Uri": "s3://healthimaging/logs/bbc4f3cccbae4095a34170fddc19b13d-DicomImport-3d8e036cc21a83e10bbb98c9d29258a5/",
        }

    return _import_job_event


@pytest.fixture
def import_job_summary():
    def _import_job_summary(*, di_upload, **kwargs):
        job_summary = {
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
        job_summary.update(kwargs)
        return job_summary

    return _import_job_summary


@pytest.mark.django_db
def test_handle_failed_job(mocker, import_job_event, import_job_summary):
    di_upload = DICOMImageSetUploadFactory()
    event = import_job_event(di_upload=di_upload, status="FAILED")
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
    mock_get_summary = mocker.patch.object(
        di_upload, "get_job_summary", return_value=job_summary
    )
    mock_get_failure_log = mocker.patch.object(
        di_upload, "get_job_output_failure_log", return_value=failure_log
    )
    spy_delete_image_sets = mocker.spy(di_upload, "delete_image_sets")

    with pytest.raises(DICOMImportJobFailedError):
        di_upload.handle_failed_job(event=event)

    mock_get_summary.assert_called_once_with(event=event)
    mock_get_failure_log.assert_called_once_with(job_summary=job_summary)
    spy_delete_image_sets.assert_called_once_with(job_summary=job_summary)
    assert di_upload.internal_failure_log == failure_log


@pytest.mark.django_db
def test_validate_image_set_no_generated_image_set(
    mocker, import_job_event, import_job_summary
):
    di_upload = DICOMImageSetUploadFactory()
    event = import_job_event(di_upload=di_upload, status="COMPLETED")
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

    with pytest.raises(DICOMImportJobFailedError):
        di_upload.validate_image_set(event=event)
    mock_get_failure_log.assert_called_once_with(job_summary=job_summary)


@pytest.mark.django_db
def test_validate_image_set_multiple_generated_image_sets(
    mocker,
    django_capture_on_commit_callbacks,
    import_job_event,
    import_job_summary,
):
    di_upload = DICOMImageSetUploadFactory()
    event = import_job_event(di_upload=di_upload, status="COMPLETED")
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
        "grandchallenge.cases.tasks.delete_healthimaging_image_set.signature",
        return_value=mock_signature,
    )

    with (
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(DICOMImportJobValidationError) as e,
    ):
        di_upload.validate_image_set(event=event)
    assert str(e.value) == "Multiple image sets created. Expected only one."
    assert mock_delete_image_set_task.call_count == 2
    mock_delete_image_set_task.assert_any_call(
        kwargs=dict(image_set_id=image_set_id_1)
    )
    mock_delete_image_set_task.assert_any_call(
        kwargs=dict(image_set_id=image_set_id_2)
    )
    assert mock_signature.apply_async.call_count == 2


@pytest.mark.django_db
def test_validate_image_set_generated_image_set_not_primary(
    mocker,
    django_capture_on_commit_callbacks,
    import_job_event,
    import_job_summary,
):
    di_upload = DICOMImageSetUploadFactory()
    event = import_job_event(di_upload=di_upload, status="COMPLETED")
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
        "grandchallenge.cases.tasks.delete_healthimaging_image_set.signature",
        return_value=mock_signature,
    )

    with (
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(DICOMImportJobValidationError) as e,
    ):
        di_upload.validate_image_set(event=event)
    assert (
        str(e.value)
        == "New instance is not primary: metadata conflicts with already existing instance."
    )
    mock_delete_image_set_task.assert_called_once_with(
        kwargs=dict(image_set_id=image_set_id)
    )
    assert mock_signature.apply_async.call_count == 1


@pytest.mark.django_db
def test_validate_image_set_generated_image_set_not_first_version(
    mocker,
    django_capture_on_commit_callbacks,
    import_job_event,
    import_job_summary,
):
    di_upload = DICOMImageSetUploadFactory()
    event = import_job_event(di_upload=di_upload, status="COMPLETED")
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
        pytest.raises(DICOMImportJobValidationError) as e,
    ):
        di_upload.validate_image_set(event=event)
    assert str(e.value) == "Instance already exists. This should never happen!"
    mock_revert_image_set_to_initial_version.assert_called_once_with(
        kwargs=dict(image_set_id=image_set_id, version_id=2)
    )
    assert mock_signature.apply_async.call_count == 1


@pytest.mark.django_db
def test_handle_completed_job_generated_image_set(
    mocker, import_job_event, import_job_summary
):
    di_upload = DICOMImageSetUploadFactory()
    event = import_job_event(di_upload=di_upload, status="COMPLETED")
    job_summary = import_job_summary(di_upload=di_upload)
    mocker.patch.object(di_upload, "get_job_summary", return_value=job_summary)
    mock_convert_image_set_to_internal = mocker.patch.object(
        di_upload, "convert_image_set_to_internal"
    )

    di_upload.handle_completed_job(event=event)

    mock_convert_image_set_to_internal.assert_called_once_with(
        image_set_id=job_summary["imageSetsSummary"][0]["imageSetId"],
    )


@pytest.mark.django_db
def test_delete_dicom_image_set_post_delete_image():
    dicom_image_set = DICOMImageSetFactory()
    image = ImageFactory(dicom_image_set=dicom_image_set)

    assert DICOMImageSet.objects.count() != 0

    image.delete()

    assert DICOMImageSet.objects.count() == 0


@pytest.mark.django_db
def test_delete_healthimaging_image_set_post_delete_dicom_image_set(
    django_capture_on_commit_callbacks,
    mocker,
):
    dicom_image_set = DICOMImageSetFactory()
    mock_signature = MagicMock()
    mock_signature.apply_async = MagicMock()
    mock_delete_healthimaging_image_set = mocker.patch(
        "grandchallenge.cases.tasks.delete_healthimaging_image_set.signature",
        return_value=mock_signature,
    )

    with django_capture_on_commit_callbacks(execute=True):
        dicom_image_set.delete()

    mock_delete_healthimaging_image_set.assert_called_once_with(
        kwargs=dict(image_set_id=dicom_image_set.image_set_id)
    )
    assert mock_signature.apply_async.call_count == 1


@pytest.mark.django_db
def test_convert_image_set_to_internal(mocker):
    dicom_image_set_upload = DICOMImageSetUploadFactory()
    image_set_id = "e616d1f717da6f80fed6271ad184b7f0"
    mocker.patch.object(
        dicom_image_set_upload,
        "get_image_set_metadata",
    )
    mocker.patch.object(
        dicom_image_set_upload,
        "convert_image_set_metadata_to_image_kwargs",
        return_value=dict(
            height=10,
            width=11,
        ),
    )

    assert Image.objects.count() == 0
    assert DICOMImageSet.objects.count() == 0

    dicom_image_set_upload.convert_image_set_to_internal(
        image_set_id=image_set_id,
    )

    assert Image.objects.count() == 1
    assert DICOMImageSet.objects.count() == 1

    dicom_image_set = DICOMImageSet.objects.first()

    assert dicom_image_set.image_set_id == image_set_id

    image = Image.objects.first()

    assert image.height == 10
    assert image.width == 11


@pytest.fixture
def image_set_metadata():
    return {
        "SchemaVersion": "1.1",
        "DatastoreID": "5bb1dcedf7c14ece969d7fe73c5b87a1",
        "ImageSetID": "3a19e171a2a4f56dd78abf493bd07bda",
        "Patient": {
            "DICOM": {
                "DeidentificationMethod": [
                    "Deidentified",
                    "Descriptors removed",
                    "Patient Characteristics removed",
                    "Device identity removed",
                    "Institution identity removed",
                    "Dates modified",
                    "Unsafe private removed",
                    "UIDs remapped",
                ],
                "DeidentificationMethodCodeSequence": [
                    {
                        "CodeValue": "113100",
                        "CodingSchemeDesignator": "DCM",
                        "CodeMeaning": "Basic Application Confidentiality Profile",
                    },
                    {
                        "CodeValue": "210004",
                        "CodingSchemeDesignator": "99PMP",
                        "CodeMeaning": "Remove all descriptors",
                    },
                    {
                        "CodeValue": "113107",
                        "CodingSchemeDesignator": "DCM",
                        "CodeMeaning": "Retain Longitudinal Temporal Information Modified Dates Option",
                    },
                    {
                        "CodeValue": "113111",
                        "CodingSchemeDesignator": "DCM",
                        "CodeMeaning": "Retain Safe Private Option",
                    },
                    {
                        "CodeValue": "210001",
                        "CodingSchemeDesignator": "99PMP",
                        "CodeMeaning": "Remap UIDs",
                    },
                ],
                "PatientBirthDate": None,
                "PatientID": "NOID",
                "PatientIdentityRemoved": "YES",
                "PatientName": "NAME^NONE",
                "PatientSex": None,
            }
        },
        "Study": {
            "DICOM": {
                "AccessionNumber": None,
                "ReferringPhysicianName": None,
                "StudyDate": "20000101",
                "StudyID": None,
                "StudyInstanceUID": "1.3.6.1.4.1.5962.99.1.5128099.2103784727.1533308485539.4.0",
                "StudyTime": "000000.000",
            },
            "Series": {
                "1.3.6.1.4.1.5962.99.1.5128099.2103784727.1533308485539.5.0": {
                    "DICOM": {
                        "DeviceSerialNumber": "SN000000",
                        "FrameOfReferenceUID": "1.3.6.1.4.1.5962.99.1.5128099.2103784727.1533308485539.6.0",
                        "Manufacturer": "Imaging Sciences International",
                        "ManufacturerModelName": "i-CAT",
                        "Modality": "CT",
                        "PositionReferenceIndicator": None,
                        "SeriesDate": "20000101",
                        "SeriesInstanceUID": "1.3.6.1.4.1.5962.99.1.5128099.2103784727.1533308485539.5.0",
                        "SeriesNumber": "1 ",
                        "SeriesTime": "000000.000",
                        "SoftwareVersions": ["3.1.62"],
                    },
                    "Instances": {
                        "1.3.6.1.4.1.5962.99.1.5128099.2103784727.1533308485539.26.0": {
                            "DICOM": {
                                "FileMetaInformationGroupLength": 218,
                                "FileMetaInformationVersion": "AAE=",
                                "MediaStorageSOPClassUID": "1.2.840.10008.5.1.4.1.1.2",
                                "MediaStorageSOPInstanceUID": "1.3.6.1.4.1.5962.99.1.5128099.2103784727.1533308485539.26.0",
                                "TransferSyntaxUID": "1.2.840.10008.1.2.4.51",
                                "ImplementationClassUID": "1.3.6.1.4.1.5962.99.2",
                                "ImplementationVersionName": "PIXELMEDJAVA001",
                                "SourceApplicationEntityTitle": "STUDIO5_11112",
                                "ImageType": ["DERIVED", "PRIMARY", "AXIAL"],
                                "InstanceCreationDate": "20000101",
                                "InstanceCreationTime": "000000.000",
                                "SOPClassUID": "1.2.840.10008.5.1.4.1.1.2",
                                "SOPInstanceUID": "1.3.6.1.4.1.5962.99.1.5128099.2103784727.1533308485539.26.0",
                                "AcquisitionDate": "20000101",
                                "ContentDate": "20000101",
                                "AcquisitionTime": "131344.000",
                                "ContentTime": "000000.000",
                                "SourceImageSequence": [
                                    {
                                        "ReferencedSOPClassUID": "1.2.840.10008.5.1.4.1.1.2",
                                        "ReferencedSOPInstanceUID": "1.3.6.1.4.1.5962.99.1.5128099.2103784727.1533308485539.25.0",
                                        "PurposeOfReferenceCodeSequence": [
                                            {
                                                "CodeValue": "121320",
                                                "CodingSchemeDesignator": "DCM",
                                                "CodeMeaning": "Uncompressed predecessor",
                                            }
                                        ],
                                    }
                                ],
                                "DerivationCodeSequence": [
                                    {
                                        "CodeValue": "113040",
                                        "CodingSchemeDesignator": "DCM",
                                        "CodeMeaning": "Lossy Compression",
                                    }
                                ],
                                "SliceThickness": "0.25",
                                "KVP": "120 ",
                                "FrameTime": "67",
                                "DistanceSourceToDetector": "699.29",
                                "DistanceSourceToPatient": "478.0145",
                                "GantryDetectorTilt": "0.0 ",
                                "RotationDirection": "CW",
                                "XRayTubeCurrent": "36",
                                "DetectorPrimaryAngle": "341 ",
                                "DetectorSecondaryAngle": "701.011962890625",
                                "ContributingEquipmentSequence": [
                                    {
                                        "Manufacturer": "PixelMed",
                                        "StationName": "STUDIO5_11112",
                                        "ManufacturerModelName": "DicomCleaner",
                                        "SoftwareVersions": [
                                            "Thu Apr 19 11:14:42 EDT 2018"
                                        ],
                                        "ContributionDateTime": "20180803160125.605+0100",
                                        "ContributionDescription": "Cleaned",
                                        "PurposeOfReferenceCodeSequence": [
                                            {
                                                "CodeValue": "109104",
                                                "CodingSchemeDesignator": "DCM",
                                                "CodeMeaning": "De-identifying Equipment",
                                            }
                                        ],
                                    }
                                ],
                                "AcquisitionNumber": None,
                                "InstanceNumber": "11",
                                "PatientOrientation": ["L", "P"],
                                "ImagePositionPatient": [
                                    "0.000000",
                                    "0.000000",
                                    "-2.625000 ",
                                ],
                                "ImageOrientationPatient": [
                                    "1.000000",
                                    "0.000000",
                                    "0.000000",
                                    "0.000000",
                                    "1.000000",
                                    "0.000000 ",
                                ],
                                "SliceLocation": "-2.625000 ",
                                "SamplesPerPixel": 1,
                                "PhotometricInterpretation": "MONOCHROME2",
                                "NumberOfFrames": "1 ",
                                "Rows": 640,
                                "Columns": 640,
                                "PixelSpacing": ["0.25", "0.25 "],
                                "PixelAspectRatio": ["1", "1 "],
                                "BitsAllocated": 16,
                                "BitsStored": 12,
                                "HighBit": 11,
                                "PixelRepresentation": 0,
                                "WindowCenter": ["0 "],
                                "WindowWidth": ["0 "],
                                "RescaleIntercept": "-1000 ",
                                "RescaleSlope": "1 ",
                                "RescaleType": "HU",
                                "LossyImageCompression": "01",
                                "LossyImageCompressionRatio": ["27.951"],
                                "LossyImageCompressionMethod": ["ISO_10918_1"],
                            },
                            "DICOMVRs": {},
                            "StoredTransferSyntaxUID": "1.2.840.10008.1.2.4.202",
                            "ChecksumType": "DECOMPRESSED",
                            "ImageFrames": [
                                {
                                    "ID": "586e9e248987bf6aa761ff5b9d790473",
                                    "PixelDataChecksumFromBaseToFullResolution": [
                                        {
                                            "Width": 640,
                                            "Height": 640,
                                            "Checksum": 989529591,
                                        }
                                    ],
                                    "MinPixelValue": 0,
                                    "MaxPixelValue": 2025,
                                    "FrameSizeInBytes": 168371,
                                }
                            ],
                        }
                    },
                }
            },
        },
    }


@pytest.mark.django_db
def test_convert_(image_set_metadata):
    modality = ImagingModalityFactory(modality="CT")
    dicom_image_set_upload = DICOMImageSetUploadFactory()
    image_kwargs = (
        dicom_image_set_upload.convert_image_set_metadata_to_image_kwargs(
            image_set_metadata
        )
    )

    assert image_kwargs == dict(
        height=640,
        width=640,
        modality=modality,
        study_instance_uid="1.3.6.1.4.1.5962.99.1.5128099.2103784727.1533308485539.4.0",
        study_date=datetime(2000, 1, 1),
        series_instance_uid="1.3.6.1.4.1.5962.99.1.5128099.2103784727.1533308485539.5.0",
    )
