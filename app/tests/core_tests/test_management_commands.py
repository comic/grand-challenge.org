import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command


@pytest.mark.django_db
def test_initdemo(settings):
    call_command("check_permissions")

    settings.DEBUG = False
    with pytest.raises(RuntimeError):
        # It should error out in production mode
        call_command("init_gc_demo")

    settings.DEBUG = True
    call_command("init_gc_demo")

    # It should create a number of users
    assert get_user_model().objects.all().count() == 10

    # Should be able to run it twice without changing the db
    call_command("init_gc_demo")

    assert get_user_model().objects.all().count() == 10
