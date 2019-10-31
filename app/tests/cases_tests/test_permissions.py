from dataclasses import dataclass

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, Group, User

from grandchallenge.cases.permissions import ImagePermission
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
