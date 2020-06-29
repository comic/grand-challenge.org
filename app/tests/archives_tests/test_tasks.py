import pytest

from grandchallenge.archives.tasks import add_images_to_archive
from tests.archives_tests.factories import ArchiveFactory
from tests.factories import ImageFactory


@pytest.mark.django_db
def test_add_images_is_idempotent():
    archive = ArchiveFactory()
    image = ImageFactory()

    image.origin.archive = archive
    image.origin.save()

    assert archive.images.count() == 1

    add_images_to_archive(upload_session_pk=image.origin.pk)

    assert archive.images.count() == 2

    add_images_to_archive(upload_session_pk=image.origin.pk)

    assert archive.images.count() == 2
