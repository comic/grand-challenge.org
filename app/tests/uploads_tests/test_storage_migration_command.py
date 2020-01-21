import os

import pytest
from django.core.files.storage import FileSystemStorage
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from grandchallenge.core.management.commands.init_gc_demo import (
    get_temporary_image,
)
from tests.factories import PageFactory


@pytest.mark.django_db(transaction=True)
def test_summernote_file_migration():
    executor = MigrationExecutor(connection)
    app = "uploads"
    model = "SummernoteAttachment"
    migrate_from = [(app, "0002_summernoteattachment")]
    migrate_to = [(app, "0003_auto_20200120_1753")]

    executor.migrate(migrate_from)
    old_apps = executor.loader.project_state(migrate_from).apps
    new_apps = executor.loader.project_state(migrate_to).apps

    OldSummernoteAttachment = old_apps.get_model(app, model)  # noqa: N806
    old_sa = OldSummernoteAttachment.objects.create(file=get_temporary_image())

    assert isinstance(old_sa.file.storage, FileSystemStorage)
    old_file_path = FileSystemStorage().path(old_sa.file.name)
    assert os.path.exists(old_file_path)

    # Reload
    executor.loader.build_graph()
    # Migrate forwards
    executor.migrate(migrate_to)

    NewSummernoteAttachment = new_apps.get_model(app, model)  # noqa: N806
    new_sa = NewSummernoteAttachment.objects.get(pk=old_sa.pk)

    assert not isinstance(new_sa.file.storage, FileSystemStorage)
    assert FileSystemStorage().path(new_sa.file.name) == old_file_path
    assert not new_sa.file.storage.exists(new_sa.file.name)

    page = PageFactory(html=f'<img src="{old_sa.file.url}" width=100px></img>')

    call_command("migrate_summernote_attachments")

    page.refresh_from_db()

    assert page.html == f'<img src="{new_sa.file.url}" width=100px></img>'
    assert new_sa.file.storage.exists(new_sa.file.name)

    os.remove(old_file_path)
    new_sa.file.delete()
