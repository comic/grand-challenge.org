import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from guardian.utils import get_anonymous_user

from tests.factories import UserFactory


@pytest.mark.django_db
def test_new_user_added_to_groups():
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)
    g_reg_anon = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )
    u = UserFactory()

    assert u.groups.filter(pk=g_reg.pk).exists()
    assert u.groups.filter(pk=g_reg_anon.pk).exists()


@pytest.mark.django_db
def test_anon_user_membership():
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)
    g_reg_anon = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )
    anon = get_anonymous_user()

    assert not anon.groups.filter(pk=g_reg.pk).exists()
    assert anon.groups.filter(pk=g_reg_anon.pk).exists()


@pytest.mark.django_db
def test_group_sizes():
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)
    g_reg_anon = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )

    n_users = get_user_model().objects.count()

    assert g_reg_anon.user_set.count() == n_users
    assert g_reg.user_set.count() == n_users - 1
