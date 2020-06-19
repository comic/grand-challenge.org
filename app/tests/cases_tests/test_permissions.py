from dataclasses import dataclass

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, Group, User
from guardian.shortcuts import get_perms

from grandchallenge.cases.permissions import ImagePermission
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.components_tests.factories import ComponentInterfaceValueFactory
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
def test_image_permission_with_public_job():
    g_reg_anon = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)

    job = AlgorithmJobFactory()

    output_image = ImageFactory()
    civ = ComponentInterfaceValueFactory(image=output_image)
    job.outputs.add(civ)

    assert "view_image" not in get_perms(g_reg, output_image)
    assert "view_image" not in get_perms(g_reg_anon, output_image)
    assert "view_image" not in get_perms(g_reg, job.inputs.first().image)
    assert "view_image" not in get_perms(g_reg_anon, job.inputs.first().image)

    job.public = True
    job.save()

    assert "view_image" not in get_perms(g_reg, output_image)
    assert "view_image" in get_perms(g_reg_anon, output_image)
    assert "view_image" not in get_perms(g_reg, job.inputs.first().image)
    assert "view_image" in get_perms(g_reg_anon, job.inputs.first().image)

    job.public = False
    job.save()

    assert "view_image" not in get_perms(g_reg, output_image)
    assert "view_image" not in get_perms(g_reg_anon, output_image)
    assert "view_image" not in get_perms(g_reg, job.inputs.first().image)
    assert "view_image" not in get_perms(g_reg_anon, job.inputs.first().image)


@pytest.mark.django_db
def test_add_image_to_public_result():
    g_reg_anon = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)

    job = AlgorithmJobFactory(public=True)
    civ_images = (
        ComponentInterfaceValueFactory(image=ImageFactory()),
        ComponentInterfaceValueFactory(image=ImageFactory()),
    )

    for im in civ_images:
        assert "view_image" not in get_perms(g_reg, im.image)
        assert "view_image" not in get_perms(g_reg_anon, im.image)

    job.outputs.add(*civ_images)

    for im in civ_images:
        assert "view_image" not in get_perms(g_reg, im.image)
        assert "view_image" in get_perms(g_reg_anon, im.image)

    job.outputs.remove(civ_images[0].pk)

    assert "view_image" not in get_perms(g_reg, civ_images[0].image)
    assert "view_image" not in get_perms(g_reg_anon, civ_images[0].image)
    assert "view_image" not in get_perms(g_reg, civ_images[1].image)
    assert "view_image" in get_perms(g_reg_anon, civ_images[1].image)

    job.outputs.clear()

    for im in civ_images:
        assert "view_image" not in get_perms(g_reg, im.image)
        assert "view_image" not in get_perms(g_reg_anon, im.image)


@pytest.mark.django_db
def test_used_by_other_public_result_permissions():
    g_reg_anon = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)

    j1 = AlgorithmJobFactory(public=True)
    j2 = AlgorithmJobFactory(public=True)

    shared_image = ImageFactory()

    civ1 = ComponentInterfaceValueFactory(image=shared_image)
    j1.outputs.add(civ1)
    civ2 = ComponentInterfaceValueFactory(image=shared_image)
    j2.outputs.add(civ2)

    assert "view_image" not in get_perms(g_reg, shared_image)
    assert "view_image" in get_perms(g_reg_anon, shared_image)

    j2.outputs.clear()

    assert "view_image" not in get_perms(g_reg, shared_image)
    assert "view_image" in get_perms(g_reg_anon, shared_image)

    j2.outputs.add(civ2)
    j2.public = False
    j2.save()

    assert "view_image" not in get_perms(g_reg, shared_image)
    assert "view_image" in get_perms(g_reg_anon, shared_image)

    j1.public = False
    j1.save()

    assert "view_image" not in get_perms(g_reg, shared_image)
    assert "view_image" not in get_perms(g_reg_anon, shared_image)


@pytest.mark.django_db
def test_change_job_image():
    g_reg_anon = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)

    job = AlgorithmJobFactory(public=True)

    assert "view_image" not in get_perms(g_reg, job.inputs.first().image)
    assert "view_image" in get_perms(g_reg_anon, job.inputs.first().image)
