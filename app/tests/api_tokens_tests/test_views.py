import pytest
from django.conf import settings
from django.urls import reverse

from tests.api_tokens_tests.factories import AuthTokenFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize("view", ("list",))
def test_logged_in_views(client, view):
    viewname = f"api-tokens:{view}"

    response = get_view_for_user(client=client, viewname=viewname, user=None)

    assert response.status_code == 302
    assert response.url == f"{settings.LOGIN_URL}?next={reverse(viewname)}"


@pytest.mark.django_db
def test_list_view_is_filtered(client):
    # AuthToken.create returns a tuple of (AuthToken, token) rather than just
    # an AuthToken, create_batch will return a list of these
    tokens = AuthTokenFactory.create_batch(2)

    response = get_view_for_user(
        client=client, viewname="api-tokens:list", user=tokens[0][0].user
    )

    assert response.status_code == 200
    assert len(response.context[-1]["object_list"]) == 1
    assert tokens[0][0] in response.context[-1]["object_list"]
    assert tokens[1][0] not in response.context[-1]["object_list"]
