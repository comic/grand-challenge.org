import hashlib
import hmac

import pytest

from grandchallenge.github.models import GitHubWebhookMessage
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_github_webhook(client, settings):
    settings.GITHUB_WEBHOOK_SECRET = "secret"

    signature = hmac.new(
        bytes(settings.GITHUB_WEBHOOK_SECRET, encoding="utf8"),
        msg=b'{"test": "test"}',
        digestmod=hashlib.sha256,
    ).hexdigest()
    signature = f"sha256={signature}"

    assert GitHubWebhookMessage.objects.count() == 0
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="api:github-webhook",
        data={"test": "test"},
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=signature[:-1],
    )

    assert response.status_code == 403
    assert GitHubWebhookMessage.objects.count() == 0

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="api:github-webhook",
        data={"test": "test"},
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=signature,
    )

    assert response.status_code == 200
    assert GitHubWebhookMessage.objects.count() == 1
