import hashlib
import hmac
import json
from unittest.mock import patch

import pytest
from requests.models import Response

from grandchallenge.github.models import GitHubWebhookMessage
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.factories import UserFactory
from tests.github_tests.factories import GitHubUserTokenFactory
from tests.utils import get_view_for_user
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
def test_github_webhook(client, settings):
    settings.GITHUB_WEBHOOK_SECRET = "secret"
    user = UserFactory()
    VerificationFactory(user=user, is_verified=True)
    token = GitHubUserTokenFactory(user=user)
    data = {"test": "test", "sender": {"id": token.github_user_id}}
    signature = hmac.new(
        bytes(settings.GITHUB_WEBHOOK_SECRET, encoding="utf8"),
        msg=json.dumps(data).encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    signature = f"sha256={signature}"

    assert GitHubWebhookMessage.objects.count() == 0
    response = get_view_for_user(
        client=client,
        method=client.post,
        user=user,
        viewname="api:github-webhook",
        data=data,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=signature[:-1],
    )

    assert response.status_code == 403
    assert GitHubWebhookMessage.objects.count() == 0

    response = get_view_for_user(
        client=client,
        method=client.post,
        user=user,
        viewname="api:github-webhook",
        data=data,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=signature,
    )

    assert response.status_code == 200
    assert GitHubWebhookMessage.objects.count() == 1


@pytest.mark.django_db
@patch("grandchallenge.github.views.requests.post")
@patch("grandchallenge.github.views.requests.get")
def test_redirect_view(get, post, client):
    resp = Response()
    resp.status_code = 200
    resp.headers["Content-Type"] = "application/json"
    resp._content = b'{"access_token": "tok", "expires_in": "3600", "refresh_token": "ref", "refresh_token_expires_in":"7200", "id": 1}'
    post.return_value = resp
    get.return_value = resp
    user = UserFactory()
    response = get_view_for_user(
        client=client,
        viewname="github:install-complete",
        data={"state": "None"},
        user=user,
    )
    assert response.status_code == 404
    error_msg = (
        '<div class="mb-2">Unfortunately something went wrong while trying '
        "to find the requested algorithm.</div><div>If you were trying to "
        "link a github repository to an algorithm, please do so manually in "
        "the algorithm's settings.</div>"
    )
    assert error_msg in response.content.decode("utf-8")

    alg = AlgorithmFactory()
    alg.add_editor(user)

    response = get_view_for_user(
        client=client,
        viewname="github:install-complete",
        data={"state": alg.slug},
        user=user,
        follow=True,
    )

    # User is not verified
    assert response.status_code == 403

    VerificationFactory(user=user, is_verified=True)
    response = get_view_for_user(
        client=client,
        viewname="github:install-complete",
        data={"state": alg.slug},
        user=user,
        follow=True,
    )

    assert response.status_code == 200
    assert f"Add GitHub repository to {alg.title}" in response.rendered_content
