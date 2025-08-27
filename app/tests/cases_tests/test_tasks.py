import shutil
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.db import IntegrityError
from panimg.models import ImageType, PanImgFile, PostProcessorResult
from panimg.post_processors import DEFAULT_POST_PROCESSORS

from grandchallenge.cases.models import (
    DicomImageSetUpload,
    DicomImageSetUploadStatusChoices,
    Image,
    ImageFile,
    PostProcessImageTask,
    PostProcessImageTaskStatusChoices,
)
from grandchallenge.cases.tasks import (
    POST_PROCESSORS,
    _check_post_processor_result,
    execute_post_process_image_task,
    import_dicom_to_healthimaging,
    import_images,
)
from grandchallenge.core.celery import acks_late_micro_short_task
from grandchallenge.core.storage import protected_s3_storage
from tests.cases_tests import RESOURCE_PATH
from tests.cases_tests.factories import DicomImageSetUploadFactory
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
def test_import_dicom_to_healthimaging_for_not_pending_upload():
    di_upload = DicomImageSetUploadFactory(
        status=DicomImageSetUploadStatusChoices.STARTED
    )

    with pytest.raises(RuntimeError):
        di_upload.start_dicom_import_job()


@pytest.mark.django_db
def test_import_dicom_to_healthimaging_updates_status_when_successful(
    settings, django_capture_on_commit_callbacks
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    di_upload = DicomImageSetUploadFactory()
    with patch.object(
        DicomImageSetUpload, "start_dicom_import_job"
    ) as mocked_method:
        with django_capture_on_commit_callbacks(execute=True):
            import_dicom_to_healthimaging(
                dicom_imageset_upload_pk=di_upload.pk
            )

        mocked_method.assert_called_once()

    di_upload.refresh_from_db()
    assert di_upload.status == DicomImageSetUploadStatusChoices.STARTED
