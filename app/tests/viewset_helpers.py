from rest_framework.test import force_authenticate
import factory
import json
from grandchallenge.subdomains.utils import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from django.db import transaction


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
    authenticated=False,
    required_relations={},
    serializer=None,
):
    # get model
    if model_factory:
        if action_name == "create" or action_name == "update":
            model = model_factory()
            model_build = model_factory.build()
            model_serialized = serializer(model_build).data
            # create related models
            relations = {}
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
        url = reverse(f"{namespace}:{model_name}-list")
    else:
        url = reverse(
            f"{namespace}:{model_name}-detail", kwargs={"pk": model.pk}
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
    if authenticated:
        user = get_user_model().objects.create_user(**TEST_USER_CREDENTIALS)
        force_authenticate(request, user=user)

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
):
    for action_name, request_method, authenticated_status in actions:
        for authenticated in (False, True):

            test_method = create_test_method(
                viewset,
                model_name,
                namespace,
                action_name,
                request_method,
                model_factory,
                authenticated,
                required_relations,
                authenticated_status,
                serializer,
            )

            test_method.__name__ = "test_{}_viewset_{}_{}".format(
                model_name,
                action_name,
                "authenticated" if authenticated else "non_authenticated",
            )
            setattr(test_class, test_method.__name__, test_method)


def create_test_method(
    viewset,
    model_name,
    namespace,
    action_name,
    request_method,
    model_factory,
    authenticated,
    required_relations,
    authenticated_status,
    serializer,
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
            authenticated=authenticated,
            required_relations=required_relations,
            serializer=serializer,
        )
        if authenticated:
            assert response_status == authenticated_status
        else:
            assert response_status == status.HTTP_401_UNAUTHORIZED

    return test_method
