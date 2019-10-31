import json

import pytest
from django.utils.encoding import force_text
from rest_framework.authtoken.models import Token

from grandchallenge.subdomains.utils import reverse
from tests.factories import UserFactory


def get_staff_user_with_token():
    user = UserFactory(is_staff=True)
    token = Token.objects.create(user=user)

    return user, token.key


@pytest.mark.django_db
@pytest.mark.parametrize("test_input, expected", [("image", "Image List")])
def test_api_pages(client, test_input, expected):
    _, token = get_staff_user_with_token()

    # Check for the correct HTML view
    url = reverse(f"api:{test_input}-list")
    response = client.get(
        url, HTTP_ACCEPT="text/html", HTTP_AUTHORIZATION="Token " + token
    )
    assert expected in force_text(response.content)
    assert response.status_code == 200

    # There should be no content, but we should be able to do json.loads
    response = client.get(
        url,
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token,
    )
    assert response.status_code == 200
    assert json.loads(response.content)["count"] == 0
