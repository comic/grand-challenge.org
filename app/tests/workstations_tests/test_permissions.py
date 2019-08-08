import pytest
from django.conf import settings
from django.contrib.auth.models import Group

from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_workstation_creators_group_exists():
    assert Group.objects.get(name=settings.WORKSTATIONS_CREATORS_GROUP_NAME)


@pytest.mark.django_db
def test_create_view_permission(client):
    u = UserFactory()
    g = Group.objects.get(name=settings.WORKSTATIONS_CREATORS_GROUP_NAME)

    response = get_view_for_user(
        client=client, user=u, viewname="workstations:create"
    )
    assert response.status_code == 403

    g.user_set.add(u)

    response = get_view_for_user(
        client=client, user=u, viewname="workstations:create"
    )
    assert response.status_code == 200
