from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from tests.viewset_helpers import TEST_USER_CREDENTIALS


def get_user_from_str(user=None):
    try:
        return get_user_model().objects.get(
            username=TEST_USER_CREDENTIALS["username"]
        )
    except get_user_model().DoesNotExist:
        if user == "staff":
            user = get_user_model().objects.create_superuser(
                **TEST_USER_CREDENTIALS
            )
        elif user == "retina_user":
            user = get_user_model().objects.create_user(
                **TEST_USER_CREDENTIALS
            )
            grader_group, group_created = Group.objects.get_or_create(
                name=settings.RETINA_GRADERS_GROUP_NAME
            )
            grader_group.user_set.add(user)
        elif user == "normal":
            user = get_user_model().objects.create_user(
                **TEST_USER_CREDENTIALS
            )
        return user


def client_login(client, user=None):
    user = get_user_from_str(user)
    if user is not None and not isinstance(user, str):
        client.login(**TEST_USER_CREDENTIALS)
    return client, user


def client_force_login(client, user=None):
    user = get_user_from_str(user)
    if user is not None and not isinstance(user, str):
        client.force_login(user=user)
    return client, user
