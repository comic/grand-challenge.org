import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command

from tests.factories import WorkstationFactory


@pytest.mark.django_db
def test_workstation_group_migration():
    # Migration 0004 is not reversible if data already exists in the table
    # so start with migration 0003 (post data migration to add the groups)
    call_command("migrate", "workstations", "0003")

    ws = WorkstationFactory()

    assert ws.editors_group
    assert ws.users_group

    # Test group removal
    call_command("migrate", "workstations", "0002")

    ws.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        assert ws.editors_group is None

    with pytest.raises(ObjectDoesNotExist):
        assert ws.users_group is None

    # Test group addition
    call_command("migrate", "workstations", "0003")

    ws.refresh_from_db()

    assert ws.editors_group
    assert ws.users_group

    # Test that 0004 does not error out
    call_command("migrate", "workstations", "0004")
