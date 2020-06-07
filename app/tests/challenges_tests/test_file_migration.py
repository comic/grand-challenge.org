import uuid

import pytest
from django.conf import settings
from django.core.files import File
from django.core.management import call_command
from django.utils.text import get_valid_filename

from grandchallenge.cases.models import image_file_path
from grandchallenge.core.management.commands.init_gc_demo import (
    get_temporary_image,
)
from tests.factories import ImageFactory, ImageFileFactory


def original_image_file_path(instance, filename):
    return (
        f"{settings.IMAGE_FILES_SUBDIRECTORY}/"
        f"{instance.image.pk}/"
        f"{get_valid_filename(filename)}"
    )


@pytest.mark.django_db
def test_image_file_migration():
    filename = f"{uuid.uuid4()}.zraw"

    i = ImageFactory()
    f = ImageFileFactory(image=i)
    f.file.save(filename, File(get_temporary_image()))

    old_name = image_file_path(f, filename)
    new_name = original_image_file_path(f, filename)

    storage = f.file.storage
    old_file_size = f.file.file.size

    assert old_name != new_name
    assert f.file.name == old_name
    assert storage.exists(old_name)
    assert not storage.exists(new_name)

    storage.copy(from_name=old_name, to_name=new_name)
    f.file.name = new_name
    f.save()
    storage.delete(old_name)

    assert not storage.exists(old_name)
    assert storage.exists(new_name)
    f.refresh_from_db()
    assert f.file.name == new_name
    assert f.file.file.size == old_file_size

    for _ in range(2):
        call_command("migrate_images")

        assert storage.exists(old_name)
        assert not storage.exists(new_name)
        f.refresh_from_db()
        assert f.file.name == old_name
        assert f.file.file.size == old_file_size
