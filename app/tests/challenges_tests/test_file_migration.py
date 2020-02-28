import uuid

import pytest
from django.core.files import File
from django.core.management import call_command

from grandchallenge.challenges.models import Challenge, get_banner_path
from grandchallenge.core.management.commands.init_gc_demo import (
    get_temporary_image,
)
from tests.factories import ChallengeFactory


@pytest.mark.django_db
def test_banner_migration():
    filename = f"{uuid.uuid4()}.jpg"

    c = ChallengeFactory()
    c.banner.save(filename, File(get_temporary_image()))

    old_name = get_banner_path(c, filename)
    new_name = f"banners/{c.pk}/{filename}"

    storage = c.banner.storage
    old_file_size = c.banner.file.size

    assert old_name != new_name
    assert c.banner.file.name == old_name
    assert storage.exists(old_name)
    assert not storage.exists(new_name)

    storage.copy(from_name=old_name, to_name=new_name)
    c.banner.name = new_name
    c.save()
    storage.delete(old_name)

    assert not storage.exists(old_name)
    assert storage.exists(new_name)
    c = Challenge.objects.get(pk=c.pk)
    assert c.banner.name == new_name
    assert c.banner.file.size == old_file_size

    _ = ChallengeFactory()

    # Migrate the file back
    for _ in range(2):
        call_command("migrate_banners")

        assert storage.exists(old_name)
        assert not storage.exists(new_name)
        c.refresh_from_db()
        assert c.banner.file.name == old_name
        assert c.banner.file.size == old_file_size
