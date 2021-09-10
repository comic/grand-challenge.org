import hashlib
import hmac
import json
from secrets import compare_digest

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.transaction import non_atomic_requests
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from grandchallenge.github.models import GitHubUserToken, GitHubWebhookMessage


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

    payload = json.loads(request.body)
    if (
        not settings.CODEBUILD_ONLY_ALLOW_VERIFIED
        or request.user.verification.is_verified
    ):
        GitHubWebhookMessage.objects.create(payload=payload)

    return HttpResponse("ok", content_type="text/plain")


@login_required
def post_install_redirect(request):
    """
    Github apps only allow a single post install callback url.
    These cannot be dynamic, so we need a redirect to the correct alogrithm.
    """
    code = request.GET.get("code")

    resp = requests.post(
        "https://github.com/login/oauth/access_token",
        data={
            "code": code,
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
        },
        timeout=5,
        headers={"Accept": "application/vnd.github.v3+json"},
    )
    resp.raise_for_status()

    try:
        # Do not use get_or_create here as we need to manipulate
        # the payload before saving it to our model
        user_token = GitHubUserToken.objects.get(user=request.user)
    except ObjectDoesNotExist:
        user_token = GitHubUserToken(user=request.user)

    user_token.update_from_payload(payload=resp.json())
    user_token.save()

    # TODO - does this need to be "state" or can we use "algorithm"
    slug = request.GET.get("state")
    if slug == "None":
        return redirect(reverse("algorithms:no-slug"))

    return redirect(
        reverse("algorithms:add-repo", kwargs={"slug": slug})
        + f"?{request.META['QUERY_STRING']}"
    )
