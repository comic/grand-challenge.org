import pytest
from django.contrib.auth.models import Group
from guardian.shortcuts import get_group_perms

from tests.algorithms_tests.factories import AlgorithmFactory
from tests.algorithms_tests.utils import TwoAlgorithms
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


@pytest.mark.django_db
def test_algorithm_detail_view_permissions(client):
    alg_set = TwoAlgorithms()

    tests = (
        (None, alg_set.alg1, 302),
        (None, alg_set.alg2, 302),
        (alg_set.creator, alg_set.alg1, 403),
        (alg_set.creator, alg_set.alg2, 403),
        (alg_set.editor1, alg_set.alg1, 200),
        (alg_set.editor1, alg_set.alg2, 403),
        (alg_set.user1, alg_set.alg1, 200),
        (alg_set.user1, alg_set.alg2, 403),
        (alg_set.editor2, alg_set.alg1, 403),
        (alg_set.editor2, alg_set.alg2, 200),
        (alg_set.user2, alg_set.alg1, 403),
        (alg_set.user2, alg_set.alg2, 200),
        (alg_set.u, alg_set.alg1, 403),
        (alg_set.u, alg_set.alg2, 403),
    )

    for test in tests:
        response = get_view_for_user(
            url=test[1].get_absolute_url(), client=client, user=test[0]
        )
        assert response.status_code == test[2]
