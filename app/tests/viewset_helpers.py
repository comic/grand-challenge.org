import json

import factory
from rest_framework.test import force_authenticate
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, AnonymousUser
from tests.factories import UserFactory
from django.conf import settings

from grandchallenge.subdomains.utils import reverse

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


def get_response_status_viewset(
    rf,
    viewset,
    model_name,
    namespace,
    action_name,
    request_method,
    model_factory=None,
    user=None,
    required_relations={},
    serializer=None,
    extra_url_kwargs={},
):
    # get model
    if model_factory:
        if action_name == "create" or action_name == "update":
            model = model_factory()
            model_build = model_factory.build()
            model_serialized = serializer(model_build).data
            # create related models
            for relation_name, relation_factory in required_relations.items():
                if isinstance(relation_factory, list):
                    # many to many
                    model_serialized[relation_name] = []
                    for single_relation_factory in relation_factory:
                        model_serialized[relation_name].append(
                            str(single_relation_factory().pk)
                        )
                else:
                    # many to one
                    model_serialized[relation_name] = str(
                        relation_factory().pk
                    )
        else:
            model = model_factory()

    # determine url
    if action_name == "list" or action_name == "create":
        url = reverse(
            f"{namespace}:{model_name}-list", kwargs=extra_url_kwargs
        )
    else:
        url = reverse(
            f"{namespace}:{model_name}-detail",
            kwargs={"pk": model.pk, **extra_url_kwargs},
        )

    # determine request
    if action_name == "create" or action_name == "update":
        request = getattr(rf, request_method)(
            url,
            data=json.dumps(model_serialized),
            content_type="application/json",
        )
    else:
        request = getattr(rf, request_method)(url)

    view = viewset.as_view(actions={request_method: action_name})

    # authenticate user
    if user == "user":
        normal_user = UserFactory()
        force_authenticate(request, user=normal_user)
    elif user == "admin":
        staff_user = UserFactory(is_staff=True)
        force_authenticate(request, user=staff_user)
    elif user == "retina_importer":
        retina_import_user = get_user_model().objects.get(
            username=settings.RETINA_IMPORT_USER_NAME
        )
        force_authenticate(request, user=retina_import_user)

    # get response
    if action_name == "list" or action_name == "create":
        response = view(request)
    else:
        response = view(request, pk=model.pk)
    return response.status_code


def batch_test_viewset_endpoints(
    actions,
    viewset,
    model_name,
    namespace,
    model_factory,
    test_class,
    required_relations={},
    serializer=None,
    extra_url_kwargs={},
):
    for action_name, request_method, authenticated_status in actions:
        for (user, authenticated) in (
            (None, False),
            ("user", False),
            ("admin", False),
            ("retina_importer", True),
        ):

            test_method = create_test_method(
                viewset,
                model_name,
                namespace,
                action_name,
                request_method,
                model_factory,
                user,
                authenticated,
                required_relations,
                authenticated_status,
                serializer,
                extra_url_kwargs,
            )

            test_method.__name__ = "test_{}_viewset_{}_{}".format(
                model_name,
                action_name,
                "authenticated_as_{}".format(str(user)),
            )
            setattr(test_class, test_method.__name__, test_method)


def create_test_method(
    viewset,
    model_name,
    namespace,
    action_name,
    request_method,
    model_factory,
    user,
    authenticated,
    required_relations,
    authenticated_status,
    serializer,
    extra_url_kwargs={},
):
    # create test method
    def test_method(self, rf):
        response_status = get_response_status_viewset(
            rf,
            viewset,
            model_name,
            namespace,
            action_name,
            request_method,
            model_factory=model_factory,
            user=user,
            required_relations=required_relations,
            serializer=serializer,
            extra_url_kwargs=extra_url_kwargs,
        )
        if authenticated:
            assert response_status == authenticated_status
        else:
            if user is None:
                assert response_status == status.HTTP_401_UNAUTHORIZED
            else:
                assert response_status == status.HTTP_403_FORBIDDEN

    return test_method


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


def get_viewset_user_kwargs_url(
    user_type, namespace, basename, grader, model, url_name
):
    user = get_user_from_user_type(user_type, grader=grader)
    kwargs = {"user_id": grader.id}
    if url_name == "detail":
        kwargs.update({"pk": model.pk})
    url = reverse(f"{namespace}:{basename}-{url_name}", kwargs=kwargs)
    return user, kwargs, url


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
):
    if action == "list" or action == "create":
        url_name = "list"
    else:
        url_name = "detail"
    user, kwargs, url = get_viewset_user_kwargs_url(
        user_type, namespace, basename, grader, model, url_name
    )

    method = "get"  # list or retrieve
    if action == "create":
        method = "post"
    elif action == "update":
        method = "put"
    elif action == "partial_update":
        method = "patch"
    elif action == "destroy":
        method = "delete"

    request = getattr(rf, method)(url)  # list, retrieve, destroy
    if action in ("create", "update", "partial_update"):
        request = getattr(rf, method)(
            url, data=data, content_type="application/json"
        )

    view = viewset.as_view(actions={method: action})
    force_authenticate(request, user=user)
    response = view(request, **kwargs)

    if not check_response_status_code:
        return response

    if (
        user_type is None
        or user_type == "normal_user"
        or user_type == "retina_grader_non_allowed"
    ):
        assert response.status_code == status.HTTP_403_FORBIDDEN
    else:
        if action in ("list", "retrieve", "update", "partial_update"):
            assert response.status_code == status.HTTP_200_OK
        elif action == "create":
            assert response.status_code == status.HTTP_201_CREATED
        elif action == "destroy":
            assert response.status_code == status.HTTP_204_NO_CONTENT
    return response
