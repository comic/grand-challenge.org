import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_workstation_group_migration():
    executor = MigrationExecutor(connection)
    app = "workstations"
    migrate_from = [(app, "0001_initial")]
    migrate_to = [(app, "0004_auto_20190813_1302")]

    executor.migrate(migrate_from)
    old_apps = executor.loader.project_state(migrate_from).apps

    Workstation = old_apps.get_model(app, "Workstation")
    old_ws = Workstation.objects.create(title="foo")

    assert not hasattr(old_ws, "editors_group")
    assert not hasattr(old_ws, "users_group")

    # Reload
    executor.loader.build_graph()
    # Migrate forwards
    executor.migrate(migrate_to)

    new_apps = executor.loader.project_state(migrate_to).apps

    Workstation = new_apps.get_model(app, "Workstation")
    new_ws = Workstation.objects.get(title="foo")

    assert new_ws.editors_group
    assert new_ws.users_group
    assert new_ws.slug == old_ws.slug
    assert new_ws.title == old_ws.title
