from django.conf import settings
from django.contrib.auth.models import AnonymousUser, Group
from rest_framework import status
from rest_framework.test import force_authenticate

from grandchallenge.subdomains.utils import reverse
from tests.factories import UserFactory

# Endpoints to check
VIEWSET_ACTIONS = (
    ("retrieve", "get", status.HTTP_200_OK),
    ("list", "get", status.HTTP_200_OK),
    ("destroy", "delete", status.HTTP_204_NO_CONTENT),
    ("create", "post", status.HTTP_201_CREATED),
    ("update", "put", status.HTTP_200_OK),
)

TEST_USER_CREDENTIALS = {
    "username": "test",
    "password": "test",
    "email": "test@example.com",
}


def get_user_from_user_type(user_type, grader=None):
    if user_type is None:
        return AnonymousUser()
    if user_type == "retina_grader":
        user = grader if grader else UserFactory()
        user.groups.add(
            Group.objects.get(name=settings.RETINA_GRADERS_GROUP_NAME)
        )
    elif user_type == "retina_grader_non_allowed":
        user = UserFactory()
        user.groups.add(
            Group.objects.get(name=settings.RETINA_GRADERS_GROUP_NAME)
        )
    elif user_type == "retina_admin":
        user = UserFactory()
        user.groups.add(
            Group.objects.get(name=settings.RETINA_ADMINS_GROUP_NAME)
        )
    else:  # normal_user
        user = grader if grader else UserFactory()
        user.groups.clear()
    return user


def get_viewset_url_kwargs(
    namespace, basename, grader, model, url_name, with_user=True
):
    kwargs = {}
    if with_user:
        kwargs.update({"user_id": grader.id})
    if url_name == "detail":
        kwargs.update({"pk": model.pk})
    url = reverse(f"{namespace}:{basename}-{url_name}", kwargs=kwargs)
    return url, kwargs


def view_test(
    action,
    user_type,
    namespace,
    basename,
    grader,
    model,
    rf,
    viewset,
    data=None,
    check_response_status_code=True,
    with_user=True,
):
    if not with_user and user_type == "retina_grader_non_allowed":
        user_type = "normal_user"

    user = get_user_from_user_type(user_type, grader=grader)

    url, kwargs = get_viewset_url_kwargs(
        namespace,
        basename,
        grader,
        model,
        "list" if action in ("list", "create") else "detail",
        with_user=with_user,
    )

    action_method = {
        "create": "post",
        "update": "put",
        "partial_update": "patch",
        "destroy": "delete",
    }
    method = action_method.get(action, "get")
    request = getattr(rf, method)(url)  # list, retrieve, destroy
    if action in ("create", "update", "partial_update"):
        request = getattr(rf, method)(
            url, data=data, content_type="application/json"
        )
    force_authenticate(request, user=user)
    view = viewset.as_view(actions={method: action})
    response = view(request, **kwargs)

    if check_response_status_code:
        validate_response_status_code(response.status_code, user_type, action)
    return response


def validate_response_status_code(status_code, user_type, action):
    if (
        user_type is None
        or user_type == "normal_user"
        or user_type == "retina_grader_non_allowed"
    ):
        assert status_code == status.HTTP_403_FORBIDDEN
    else:
        if action in ("list", "retrieve", "update", "partial_update"):
            assert status_code == status.HTTP_200_OK
        elif action == "create":
            assert status_code == status.HTTP_201_CREATED
        elif action == "destroy":
            assert status_code == status.HTTP_204_NO_CONTENT
