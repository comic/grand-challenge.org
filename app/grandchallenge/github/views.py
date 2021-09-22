import hashlib
import hmac
import json
from secrets import compare_digest

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.transaction import non_atomic_requests
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
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

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {user_token.access_token}",
    }

    github_user = requests.get(
        "https://api.github.com/user", headers=headers, timeout=5,
    ).json()
    user_token.github_user_id = github_user["id"]
    user_token.save()

    slug = request.GET.get("state")
    if slug == "None":
        msg = mark_safe(
            '<div class="mb-2">'
            "Unfortunately something went wrong while trying to find the requested algorithm."
            "</div>"
            "<div>"
            "If you were trying to link a github repository to an algorithm, "
            "please do so manually in the algorithm's settings."
            "</div>"
        )
        raise Http404(msg)

    return redirect(
        reverse("algorithms:add-repo", kwargs={"slug": slug})
        + f"?{request.META['QUERY_STRING']}"
    )
