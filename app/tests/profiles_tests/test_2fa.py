import pytest
from pytest_django.asserts import assertRedirects

from config.settings import LOGIN_REDIRECT_URL
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_2fa_required_for_staff(client):
    admin = UserFactory(is_staff=True)
    user = UserFactory()

    response = get_view_for_user(
        viewname="account_login",
        client=client,
        method=client.post,
        data={"login": user.username, "password": user.password},
        user=user,
    )
    assertRedirects(
        response, LOGIN_REDIRECT_URL, fetch_redirect_response=False
    )

    response = get_view_for_user(
        viewname="account_login",
        client=client,
        method=client.post,
        data={"login": admin.username, "password": admin.password},
        user=admin,
    )
    assertRedirects(
        response, "/accounts/two_factor/setup", fetch_redirect_response=False
    )
