import pytest
from django.contrib.auth.models import Group
from guardian.shortcuts import get_group_perms

from tests.algorithms_tests.factories import AlgorithmFactory
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_algorithm_creators_group_has_perm(settings):
    creators_group = Group.objects.get(
        name=settings.ALGORITHMS_CREATORS_GROUP_NAME
    )
    assert creators_group.permissions.filter(codename="add_algorithm").exists()


@pytest.mark.django_db
def test_groups_permissions_are_assigned():
    alg = AlgorithmFactory()

    editors_perms = get_group_perms(alg.editors_group, alg)
    assert "view_algorithm" in editors_perms
    assert "change_algorithm" in editors_perms

    users_perms = get_group_perms(alg.users_group, alg)
    assert "view_algorithm" in users_perms
    assert "change_algorithm" not in users_perms


@pytest.mark.django_db
def test_algorithm_create_page(client, settings):
    response = get_view_for_user(viewname="algorithms:create", client=client)
    assert response.status_code == 302
    assert response.url.startswith(settings.LOGIN_URL)

    user = UserFactory()

    response = get_view_for_user(
        viewname="algorithms:create", client=client, user=user
    )
    assert response.status_code == 403

    Group.objects.get(
        name=settings.ALGORITHMS_CREATORS_GROUP_NAME
    ).user_set.add(user)

    response = get_view_for_user(
        viewname="algorithms:create", client=client, user=user
    )
    assert response.status_code == 200
