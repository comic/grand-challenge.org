import pytest
from django.conf import settings
from django.contrib.messages import get_messages
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse

from tests.api_tokens_tests.factories import AuthTokenFactory
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize("view", ("list", "create",))
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


@pytest.mark.django_db
def test_token_is_created_for_user(client):
    user = UserFactory()

    assert not user.auth_token_set.exists()

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="api-tokens:create",
        data={},
        user=user,
    )

    assert response.status_code == 302

    token = user.auth_token_set.get()

    assert token.expiry is None

    messages = list(get_messages(response.wsgi_request))

    assert len(messages) == 1
    assert str(messages[0]).startswith(
        f"Your new API token is:<br><br><pre>{token.token_key}"
    )


@pytest.mark.django_db
def test_user_cannot_delete_token_of_another(client):
    token, _ = AuthTokenFactory()
    user = UserFactory()

    def _delete_token(u):
        return get_view_for_user(
            client=client,
            method=client.post,
            viewname="api-tokens:delete",
            reverse_kwargs={"token_key": token.token_key},
            data={},
            user=u,
        )

    # Other user cannot delete
    assert _delete_token(user).status_code == 404

    # Ensure the token still exists
    token.refresh_from_db()
    assert _delete_token(token.user).status_code == 302

    # Token deleted by the owner
    with pytest.raises(ObjectDoesNotExist):
        token.refresh_from_db()
