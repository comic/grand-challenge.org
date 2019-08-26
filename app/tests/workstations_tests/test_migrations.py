import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from guardian.shortcuts import get_perms

from grandchallenge.workstations.models import Workstation
from tests.factories import UserFactory


@pytest.mark.django_db(transaction=True)
def test_workstation_group_migration():
    executor = MigrationExecutor(connection)
    app = "workstations"
    migrate_from = [(app, "0001_initial")]
    migrate_to = [(app, "0004_auto_20190814_1402")]

    executor.migrate(migrate_from)
    old_apps = executor.loader.project_state(migrate_from).apps

    user = UserFactory()
    OldWorkstation = old_apps.get_model(app, "Workstation")
    old_ws = OldWorkstation.objects.create(title="foo")

    assert not hasattr(old_ws, "editors_group")
    assert not hasattr(old_ws, "users_group")

    # Reload
    executor.loader.build_graph()
    # Migrate forwards
    executor.migrate(migrate_to)

    new_ws = Workstation.objects.get(title="foo")
    new_ws.add_user(user=user)

    assert new_ws.editors_group
    assert new_ws.users_group
    assert new_ws.slug == old_ws.slug
    assert new_ws.title == old_ws.title
    assert "view_workstation" in get_perms(user, new_ws)

    # For some reason this migration is removed but not added back?
    # E psycopg2.errors.FeatureNotSupported: cannot truncate a table referenced
    #   in a foreign key constraint
    # E DETAIL:  Table "algorithms_algorithm" references "auth_user".
    executor.loader.build_graph()
    executor.migrate([("algorithms", "0009_auto_20190826_0951")])
