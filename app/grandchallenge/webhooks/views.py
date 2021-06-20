import hashlib
import hmac
import json
from datetime import timedelta
from secrets import compare_digest

from django.conf import settings
from django.db.transaction import non_atomic_requests
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from grandchallenge.webhooks.models import GitHubWebhookMessage


@csrf_exempt
@require_POST
@non_atomic_requests
def github_webhook(request):
    signature = hmac.new(
        bytes(settings.GITHUB_WEBHOOK_SECRET, encoding="utf8"),
        msg=request.body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    signature = f"sha256={signature}"
    if not compare_digest(
        signature, request.headers.get("X-Hub-Signature-256", "")
    ):
        return HttpResponseForbidden(
            "Signatures do not match", content_type="text/plain",
        )

    GitHubWebhookMessage.objects.filter(
        received_at__lte=timezone.now() - timedelta(days=7)
    ).delete()
    payload = json.loads(request.body)

    GitHubWebhookMessage.objects.create(
        received_at=timezone.now(), payload=payload,
    )

    return HttpResponse("ok", content_type="text/plain")


def post_install_redirect(request):
    """
    Github apps only allow a single post install callback url.
    These cannot be dynamic, so we need a redirect to the correct alogrithm.
    """
    slug = request.GET.get("state")
    return redirect(
        reverse("algorithms:add-repo", kwargs={"slug": slug})
        + f"?{request.META['QUERY_STRING']}"
    )
