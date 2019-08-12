from typing import NamedTuple

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User

from grandchallenge.workstations.models import Workstation
from tests.factories import UserFactory, WorkstationFactory
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


class WorkstationSet(NamedTuple):
    workstation: Workstation
    editor: User
    user: User


class TwoWorkstationSets(NamedTuple):
    ws1: WorkstationSet
    ws2: WorkstationSet


def workstation_set():
    ws = WorkstationFactory()
    e, u = UserFactory(), UserFactory()
    wss = WorkstationSet(workstation=ws, editor=e, user=u)
    wss.workstation.add_editor(user=e)
    wss.workstation.add_user(user=u)
    return wss


@pytest.fixture
def two_workstation_sets() -> TwoWorkstationSets:
    return TwoWorkstationSets(ws1=workstation_set(), ws2=workstation_set())


@pytest.mark.django_db
@pytest.mark.parametrize(
    "viewname", ["workstations:update", "workstations:image-create"]
)
def test_update_view_permissions(client, two_workstation_sets, viewname):
    tests = (
        (two_workstation_sets.ws1.editor, 200),
        (two_workstation_sets.ws1.user, 403),
        (two_workstation_sets.ws2.editor, 403),
        (two_workstation_sets.ws2.user, 403),
        (UserFactory(), 403),
        (UserFactory(is_staff=True), 403),
        (None, 302),
    )

    for test in tests:
        response = get_view_for_user(
            viewname=viewname,
            client=client,
            user=test[0],
            reverse_kwargs={"slug": two_workstation_sets.ws1.workstation.slug},
        )
        assert response.status_code == test[1]
