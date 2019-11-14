import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_workstation_group_migration():
    executor = MigrationExecutor(connection)
    app = "workstations"
    migrate_from = [(app, "0001_initial")]
    migrate_to = [(app, "0004_auto_20190814_1402")]

    executor.migrate(migrate_from)
    old_apps = executor.loader.project_state(migrate_from).apps
    new_apps = executor.loader.project_state(migrate_to).apps

    OldWorkstation = old_apps.get_model(app, "Workstation")  # noqa: N806
    old_ws = OldWorkstation.objects.create(title="foo")

    assert not hasattr(old_ws, "editors_group")
    assert not hasattr(old_ws, "users_group")

    # Reload
    executor.loader.build_graph()
    # Migrate forwards
    executor.migrate(migrate_to)

    NewWorkstation = new_apps.get_model(app, "Workstation")  # noqa: N806

    new_ws = NewWorkstation.objects.get(title="foo")

    assert new_ws.editors_group
    assert new_ws.users_group
    assert new_ws.slug == old_ws.slug
    assert new_ws.title == old_ws.title

    # For some reason this migration is removed but not added back?
    # E psycopg2.errors.FeatureNotSupported: cannot truncate a table referenced
    #   in a foreign key constraint
    # E DETAIL:  Table "algorithms_algorithm" references "auth_user".
    executor.loader.build_graph()
    executor.migrate([("algorithms", "0009_auto_20190826_0951")])
