from dataclasses import dataclass

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, Group, User
from guardian.shortcuts import get_perms

from grandchallenge.cases.permissions import ImagePermission
from tests.algorithms_tests.factories import AlgorithmResultFactory
from tests.factories import ImageFactory, UserFactory


@dataclass
class Request:
    user: User


@pytest.mark.django_db
class TestImagePermission:
    @pytest.mark.parametrize(
        "user,access",
        [
            (AnonymousUser, False),
            (UserFactory, False),
            ("retina_grader_no_access", False),
            ("retina_admin_no_access", False),
            ("retina_grader", True),
            ("retina_admin", True),
        ],
    )
    def test_permissions(self, user, access):
        image = ImageFactory()
        if isinstance(user, str):
            group_name = (
                settings.RETINA_ADMINS_GROUP_NAME
                if "admin" in user
                else settings.RETINA_GRADERS_GROUP_NAME
            )
            if "no_access" not in user:
                image.permit_viewing_by_retina_users()

            user = UserFactory()
            grader_group, group_created = Group.objects.get_or_create(
                name=group_name
            )
            grader_group.user_set.add(user)
        elif user == AnonymousUser:
            user = AnonymousUser()
        else:
            user = user(is_staff=True)
        request = Request(user=user)
        permission = ImagePermission()
        assert permission.has_object_permission(request, {}, image) == access


@pytest.mark.django_db
def test_image_permission_with_algorithm_result():
    g_reg_anon = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)

    result = AlgorithmResultFactory()
    result_image = ImageFactory()
    result.images.add(result_image)

    assert "view_image" not in get_perms(g_reg, result_image)
    assert "view_image" not in get_perms(g_reg_anon, result_image)
    assert "view_image" not in get_perms(g_reg, result.job.image)
    assert "view_image" not in get_perms(g_reg_anon, result.job.image)

    result.public = True
    result.save()

    assert "view_image" not in get_perms(g_reg, result_image)
    assert "view_image" in get_perms(g_reg_anon, result_image)
    assert "view_image" not in get_perms(g_reg, result.job.image)
    assert "view_image" in get_perms(g_reg_anon, result.job.image)

    result.public = False
    result.save()

    assert "view_image" not in get_perms(g_reg, result_image)
    assert "view_image" not in get_perms(g_reg_anon, result_image)
    assert "view_image" not in get_perms(g_reg, result.job.image)
    assert "view_image" not in get_perms(g_reg_anon, result.job.image)


@pytest.mark.django_db
def test_add_image_to_public_result():
    g_reg_anon = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)

    result = AlgorithmResultFactory(public=True)
    result_images = ImageFactory(), ImageFactory()

    for im in result_images:
        assert "view_image" not in get_perms(g_reg, im)
        assert "view_image" not in get_perms(g_reg_anon, im)

    result.images.add(*result_images)

    for im in result_images:
        assert "view_image" not in get_perms(g_reg, im)
        assert "view_image" in get_perms(g_reg_anon, im)

    result.images.remove(result_images[0].pk)

    assert "view_image" not in get_perms(g_reg, result_images[0])
    assert "view_image" not in get_perms(g_reg_anon, result_images[0])
    assert "view_image" not in get_perms(g_reg, result_images[1])
    assert "view_image" in get_perms(g_reg_anon, result_images[1])

    result.images.clear()

    for im in result_images:
        assert "view_image" not in get_perms(g_reg, im)
        assert "view_image" not in get_perms(g_reg_anon, im)


@pytest.mark.django_db
def test_used_by_other_public_result_permissions():
    g_reg_anon = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)

    r_a = AlgorithmResultFactory(public=True)
    r_b = AlgorithmResultFactory(public=True)

    shared_image = ImageFactory()

    r_a.images.add(shared_image)
    r_b.images.add(shared_image)

    assert "view_image" not in get_perms(g_reg, shared_image)
    assert "view_image" in get_perms(g_reg_anon, shared_image)

    r_b.images.clear()

    assert "view_image" not in get_perms(g_reg, shared_image)
    assert "view_image" in get_perms(g_reg_anon, shared_image)

    r_b.images.add(shared_image)
    r_b.public = False
    r_b.save()

    assert "view_image" not in get_perms(g_reg, shared_image)
    assert "view_image" in get_perms(g_reg_anon, shared_image)

    r_a.public = False
    r_a.save()

    assert "view_image" not in get_perms(g_reg, shared_image)
    assert "view_image" not in get_perms(g_reg_anon, shared_image)


@pytest.mark.django_db
def test_change_job_image():
    g_reg_anon = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)

    i_orig = ImageFactory()
    r = AlgorithmResultFactory(public=True, job__image=i_orig)

    assert "view_image" not in get_perms(g_reg, i_orig)
    assert "view_image" in get_perms(g_reg_anon, i_orig)

    i_new = ImageFactory()
    r.job.image = i_new
    r.job.save()

    assert "view_image" not in get_perms(g_reg, i_orig)
    assert "view_image" not in get_perms(g_reg_anon, i_orig)
    assert "view_image" not in get_perms(g_reg, i_new)
    assert "view_image" in get_perms(g_reg_anon, i_new)
