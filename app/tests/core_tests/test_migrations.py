import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_make_migration(capsys):
    """Ensure that migrations do not need to be made."""
    call_command("makemigrations")
    out, err = capsys.readouterr()
    assert out == "No changes detected\n"
    assert err == ""
