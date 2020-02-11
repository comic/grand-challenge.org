import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management import call_command


@pytest.mark.django_db
def test_make_migration(capsys):
    """Ensure that migrations do not need to be made."""
    call_command("makemigrations")
    out, err = capsys.readouterr()
    assert out == "No changes detected\n"
    assert err == ""


@pytest.mark.django_db
@pytest.mark.parametrize(
    "group",
    [
        settings.REGISTERED_AND_ANON_USERS_GROUP_NAME,
        settings.REGISTERED_USERS_GROUP_NAME,
    ],
)
def test_all_users_group_exists(group):
    assert Group.objects.get(name=group)
