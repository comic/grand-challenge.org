import shutil
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError
from django.db import IntegrityError
from grand_challenge_dicom_de_identifier.exceptions import (
    RejectedDICOMFileError,
)
from panimg.models import ImageType, PanImgFile, PostProcessorResult
from panimg.post_processors import DEFAULT_POST_PROCESSORS

from grandchallenge.cases.models import (
    DICOMImageSetUpload,
    DICOMImageSetUploadStatusChoices,
    Image,
    ImageFile,
    PostProcessImageTask,
    PostProcessImageTaskStatusChoices,
)
from grandchallenge.cases.tasks import (
    POST_PROCESSORS,
    _check_post_processor_result,
    execute_post_process_image_task,
    import_dicom_to_health_imaging,
    import_images,
)
from grandchallenge.core.celery import acks_late_micro_short_task
from grandchallenge.core.storage import protected_s3_storage
from tests.cases_tests import RESOURCE_PATH
from tests.cases_tests.factories import DICOMImageSetUploadFactory
from tests.factories import ImageFactory
from tests.utils import create_raw_upload_image_session


@pytest.mark.django_db
def test_linked_task_called_with_session_pk(
    settings, django_capture_on_commit_callbacks
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    called = {}

    @acks_late_micro_short_task
    def local_linked_task(*_, **kwargs):
        called.update(**kwargs)

    session, uploaded_images = create_raw_upload_image_session(
        image_paths=[RESOURCE_PATH / "image10x10x10.mha"],
    )

    with django_capture_on_commit_callbacks(execute=True):
        session.process_images(linked_task=local_linked_task.signature())

    assert called == {"upload_session_pk": session.pk}


def test_post_processors_setting():
    assert POST_PROCESSORS == DEFAULT_POST_PROCESSORS


def test_check_post_processor_result():
    image = Image()

    assert (
        _check_post_processor_result(
            post_processor_result=PostProcessorResult(
                new_image_files=set(),
            ),
            image=image,
        )
        is None
    )
    assert (
        _check_post_processor_result(
            post_processor_result=PostProcessorResult(
                new_image_files={
                    PanImgFile(
                        image_id=image.pk,
                        image_type=ImageType.MHD,
                        file=Path("foo"),
                    )
                },
            ),
            image=image,
        )
        is None
    )
    assert (
        _check_post_processor_result(
            post_processor_result=PostProcessorResult(
                new_image_files={
                    PanImgFile(
                        image_id=image.pk,
                        image_type=ImageType.MHD,
                        file=Path("foo"),
                        directory=Path("bar"),
                    )
                },
            ),
            image=image,
        )
        is None
    )

    with pytest.raises(RuntimeError):
        _check_post_processor_result(
            post_processor_result=PostProcessorResult(
                new_image_files={
                    PanImgFile(
                        image_id=uuid4(),
                        image_type=ImageType.MHD,
                        file=Path("foo"),
                    )
                },
            ),
            image=image,
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "filename, expected_bytes, expected_files",
    [("valid_tiff.tif", 246717, 2), ("no_dzi.tif", 258038, 1)],
)
def test_post_processing(
    filename,
    tmpdir_factory,
    settings,
    django_capture_on_commit_callbacks,
    expected_bytes,
    expected_files,
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    input_directory = tmpdir_factory.mktemp("temp")
    temp_file = Path(input_directory / filename)
    shutil.copy(RESOURCE_PATH / filename, temp_file)

    with django_capture_on_commit_callbacks() as callbacks:
        imported_images = import_images(input_directory=input_directory)

    assert len(callbacks) == 1
    assert imported_images.consumed_files == {temp_file}
    assert len(imported_images.new_images) == 1
    new_image = imported_images.new_images.pop()

    image_files = ImageFile.objects.filter(image=new_image)

    assert len(image_files) == 1
    image_file = image_files[0]

    assert (
        image_file.image.postprocessimagetask.status
        == PostProcessImageTaskStatusChoices.INITIALIZED
    )

    callbacks[0]()

    all_image_files = ImageFile.objects.filter(image=new_image)
    if filename == "valid_tiff.tif":
        assert len(all_image_files) == 2

        dzi = all_image_files.get(image_type=ImageType.DZI)
        assert protected_s3_storage.exists(str(dzi.file))
        assert protected_s3_storage.exists(
            str(dzi.file).replace(".dzi", "_files/0/0_0.jpeg")
        )
    else:
        assert len(all_image_files) == 1

    image_file.refresh_from_db()
    assert (
        image_file.image.postprocessimagetask.status
        == PostProcessImageTaskStatusChoices.COMPLETED
    )

    # Newly created images should not have a post process task created
    assert PostProcessImageTask.objects.count() == 1

    # Task should be idempotent
    execute_post_process_image_task(
        post_process_image_task_pk=image_file.image.postprocessimagetask.pk
    )

    all_image_files = ImageFile.objects.filter(image=new_image)

    assert len(all_image_files) == expected_files
    assert ImageFile.objects.count() == expected_files

    assert (
        sum(file.size_in_storage for file in ImageFile.objects.all())
        == expected_bytes
    )


@pytest.mark.django_db
def test_unique_post_processing():
    image = ImageFactory()

    PostProcessImageTask.objects.create(image=image)

    with pytest.raises(IntegrityError):
        PostProcessImageTask.objects.create(image=image)


@pytest.mark.django_db
def test_import_dicom_to_health_imaging_for_not_pending_upload():
    di_upload = DICOMImageSetUploadFactory(
        status=DICOMImageSetUploadStatusChoices.STARTED
    )

    with patch.object(DICOMImageSetUpload, "start_dicom_import_job"):
        with pytest.raises(RuntimeError):
            import_dicom_to_health_imaging(
                dicom_imageset_upload_pk=di_upload.pk
            )


@pytest.mark.django_db
def test_import_dicom_to_health_imaging_updates_status_when_successful(
    django_capture_on_commit_callbacks,
):
    di_upload = DICOMImageSetUploadFactory()
    with (
        patch.object(
            DICOMImageSetUpload, "start_dicom_import_job"
        ) as mocked_import_method,
        patch.object(DICOMImageSetUpload, "deidentify_user_uploads"),
    ):
        with django_capture_on_commit_callbacks(execute=True):
            import_dicom_to_health_imaging(
                dicom_imageset_upload_pk=di_upload.pk
            )

        mocked_import_method.assert_called_once()

    di_upload.refresh_from_db()
    assert di_upload.status == DICOMImageSetUploadStatusChoices.STARTED


@pytest.mark.django_db
def test_start_dicom_import_job_does_not_run_when_deid_fails(
    django_capture_on_commit_callbacks,
):
    di_upload = DICOMImageSetUploadFactory()
    with (
        patch.object(
            DICOMImageSetUpload, "start_dicom_import_job"
        ) as mocked_import_method,
        patch.object(
            DICOMImageSetUpload,
            "deidentify_user_uploads",
            side_effect=Exception(),
        ),
        patch.object(
            DICOMImageSetUpload,
            "delete_input_files",
        ) as mocked_delete_input_files,
    ):
        with django_capture_on_commit_callbacks(execute=True):
            import_dicom_to_health_imaging(
                dicom_imageset_upload_pk=di_upload.pk
            )
        # start_dicom_import_job does not get called
        mocked_import_method.assert_not_called()

    di_upload.refresh_from_db()
    # upload gets marked as failed
    assert di_upload.status == DICOMImageSetUploadStatusChoices.FAILED
    assert di_upload.error_message == "An unexpected error occurred"
    mocked_delete_input_files.assert_called_once()


@pytest.mark.django_db
def test_error_in_start_dicom_import_job(django_capture_on_commit_callbacks):
    di_upload = DICOMImageSetUploadFactory()

    with (
        patch.object(
            DICOMImageSetUpload,
            "start_dicom_import_job",
            side_effect=ClientError(
                error_response={
                    "Error": {"Code": "ValidationError", "Message": "Foo"}
                },
                operation_name="StartDICOMImportJob",
            ),
        ),
        patch.object(
            DICOMImageSetUpload,
            "deidentify_user_uploads",
        ),
        patch.object(
            DICOMImageSetUpload,
            "delete_input_files",
        ) as mock_delete_input_files,
    ):
        with django_capture_on_commit_callbacks(execute=True):
            import_dicom_to_health_imaging(
                dicom_imageset_upload_pk=di_upload.pk
            )

    di_upload.refresh_from_db()
    assert di_upload.status == DICOMImageSetUploadStatusChoices.FAILED
    assert di_upload.error_message == "An unexpected error occurred"
    mock_delete_input_files.assert_called_once()


@pytest.mark.django_db
def test_start_dicom_import_job_sets_error_message_when_deid_fails(
    django_capture_on_commit_callbacks, mocker
):
    di_upload = DICOMImageSetUploadFactory()

    mock_qs = mocker.MagicMock()
    mocker.patch.object(
        type(di_upload.user_uploads), "all", return_value=mock_qs
    )

    with (
        patch.object(
            DICOMImageSetUpload, "start_dicom_import_job"
        ) as mocked_import_method,
        patch.object(
            DICOMImageSetUpload,
            "deidentify_user_uploads",
            side_effect=RejectedDICOMFileError(justification="Foo"),
        ),
        patch.object(
            DICOMImageSetUpload,
            "delete_input_files",
        ) as mocked_delete_input_files,
    ):
        with django_capture_on_commit_callbacks(execute=True):
            import_dicom_to_health_imaging(
                dicom_imageset_upload_pk=di_upload.pk
            )
        # start_dicom_import_job does not get called
        mocked_import_method.assert_not_called()
        mocked_delete_input_files.assert_called_once()
        mock_qs.delete.assert_called_once()

    di_upload.refresh_from_db()
    # upload gets marked as failed
    assert di_upload.status == DICOMImageSetUploadStatusChoices.FAILED
    assert di_upload.error_message == "Foo"
