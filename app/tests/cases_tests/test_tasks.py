import shutil
from pathlib import Path
from uuid import uuid4

import pytest
from celery import shared_task
from panimg.models import ImageType, PanImgFile, PostProcessorResult
from panimg.post_processors import DEFAULT_POST_PROCESSORS

from grandchallenge.cases.models import ImageFile
from grandchallenge.cases.tasks import (
    POST_PROCESSORS,
    _check_post_processor_result,
    import_images,
    post_process_image,
)
from grandchallenge.core.storage import protected_s3_storage
from tests.cases_tests import RESOURCE_PATH
from tests.factories import UploadSessionFactory


@pytest.mark.django_db
def test_linked_task_called_with_session_pk(
    settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    called = {}

    @shared_task
    def local_linked_task(*_, **kwargs):
        called.update(**kwargs)

    session = UploadSessionFactory()

    with django_capture_on_commit_callbacks(execute=True):
        session.process_images(linked_task=local_linked_task.signature())

    assert called == {"upload_session_pk": session.pk}


def test_post_processors_setting():
    assert POST_PROCESSORS == DEFAULT_POST_PROCESSORS


def test_check_post_processor_result():
    pk = uuid4()

    assert (
        _check_post_processor_result(
            post_processor_result=PostProcessorResult(
                new_image_files=set(),
            ),
            image_pk=pk,
        )
        is None
    )
    assert (
        _check_post_processor_result(
            post_processor_result=PostProcessorResult(
                new_image_files={
                    PanImgFile(
                        image_id=pk, image_type=ImageType.MHD, file=Path("foo")
                    )
                },
            ),
            image_pk=pk,
        )
        is None
    )
    assert (
        _check_post_processor_result(
            post_processor_result=PostProcessorResult(
                new_image_files={
                    PanImgFile(
                        image_id=pk,
                        image_type=ImageType.MHD,
                        file=Path("foo"),
                        directory=Path("bar"),
                    )
                },
            ),
            image_pk=pk,
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
            image_pk=pk,
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "source_dir, filename",
    [(RESOURCE_PATH, "valid_tiff.tif"), (RESOURCE_PATH, "no_dzi.tif")],
)
def test_post_processing(
    source_dir,
    filename,
    tmpdir_factory,
    settings,
    django_capture_on_commit_callbacks,
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    input_directory = tmpdir_factory.mktemp("temp")
    temp_file = Path(input_directory / filename)
    shutil.copy(source_dir / filename, temp_file)

    with django_capture_on_commit_callbacks() as callbacks:
        imported_images = import_images(input_directory=input_directory)

    assert len(callbacks) == 1
    assert imported_images.consumed_files == {temp_file}
    assert len(imported_images.new_images) == 1
    new_image = imported_images.new_images.pop()

    image_files = ImageFile.objects.filter(image=new_image)

    assert len(image_files) == 1
    image_file = image_files[0]

    assert image_file.post_processed is False

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
    assert image_file.post_processed is True

    # Newly created images should not be marked as post processed
    assert ImageFile.objects.filter(post_processed=True).count() == 1

    # Task should be idempotent, but all related
    # files are now marked as post processed
    post_process_image(image_pk=new_image.pk)

    all_image_files = ImageFile.objects.filter(image=new_image)
    if filename == "valid_tiff.tif":
        assert len(all_image_files) == 2
        assert ImageFile.objects.count() == 2
        assert ImageFile.objects.filter(post_processed=True).count() == 2
    else:
        assert len(all_image_files) == 1
        assert ImageFile.objects.count() == 1
        assert ImageFile.objects.filter(post_processed=True).count() == 1
