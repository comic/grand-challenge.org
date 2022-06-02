import pytest
from django.conf import settings
from django.contrib.auth.models import Group


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
