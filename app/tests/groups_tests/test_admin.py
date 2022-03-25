import pytest
from django.contrib.auth.models import Group

from grandchallenge.groups.admin import GroupAdminForm
from tests.factories import UserFactory


@pytest.mark.django_db
def test_add_user_to_group(client):
    user = UserFactory()
    data = {
        "name": "dummy-group",
        "users": [user],
    }
    form = GroupAdminForm(data=data)
    form.save()
    # check if user is in group
    group = Group.objects.last()
    assert user in group.user_set.all()
