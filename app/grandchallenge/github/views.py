import hashlib
import hmac
import json
from secrets import compare_digest

import requests
from dal_select2.views import Select2ListView
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.transaction import non_atomic_requests
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.functional import cached_property
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from guardian.mixins import LoginRequiredMixin
from requests import HTTPError

from grandchallenge.github.exceptions import GitHubBadRefreshTokenException
from grandchallenge.github.models import GitHubUserToken, GitHubWebhookMessage
from grandchallenge.github.utils import (
    decode_github_state,
    encode_github_state,
)
from grandchallenge.verifications.views import VerificationRequiredMixin


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
            "Signatures do not match", content_type="text/plain"
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
    state = decode_github_state(state=request.GET.get("state"))

    code = request.GET.get("code")

    resp = requests.post(
        "https://github.com/login/oauth/access_token",
        data={
            "code": code,
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
        },
        timeout=5,
        headers={"Accept": "application/vnd.github+json"},
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
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {user_token.access_token}",
    }

    github_user = requests.get(
        "https://api.github.com/user", headers=headers, timeout=5
    ).json()
    user_token.github_user_id = github_user["id"]
    user_token.save()

    return redirect(state.redirect_url)


class GitHubInstallationRequiredMixin:
    """
    Ensures that the GitHub application is installed for the current user

    Requires the user to be logged in, use after LoginRequiredMixin.
    """

    @property
    def github_state(self):
        return encode_github_state(
            redirect_url=self.request.build_absolute_uri()
        )

    @property
    def github_auth_url(self):
        return f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}&state={self.github_state}"

    @property
    def github_app_install_url(self):
        return f"{settings.GITHUB_APP_INSTALL_URL}?state={self.github_state}"

    @cached_property
    def github_request_kwargs(self):
        return {
            "headers": {
                "Accept": "application/vnd.github+json",
                "Authorization": f"token {self.github_user_token.access_token}",
            },
            "timeout": 5,
        }

    @cached_property
    def installations(self):
        response = requests.get(
            "https://api.github.com/user/installations",
            **self.github_request_kwargs,
        )
        response.raise_for_status()
        return response.json()["installations"]

    def dispatch(self, *args, **kwargs):
        try:
            self.github_user_token = GitHubUserToken.objects.get(
                user=self.request.user
            )
        except GitHubUserToken.DoesNotExist:
            return redirect(self.github_auth_url)

        if self.github_user_token.access_token_is_expired:
            try:
                self.github_user_token.refresh_access_token()
            except (HTTPError, GitHubBadRefreshTokenException):
                self.github_user_token.delete()
                return redirect(self.github_auth_url)

            self.github_user_token.save()

        if not self.installations:
            return redirect(self.github_app_install_url)

        return super().dispatch(*args, **kwargs)


class RepositoriesList(
    LoginRequiredMixin,
    VerificationRequiredMixin,
    GitHubInstallationRequiredMixin,
    Select2ListView,
):
    raise_exception = True

    def get_repos(self, *, installation_id):
        """
        Get the repositories for this users installation

        Currently, there is no way to filter the repositories, see
        https://docs.github.com/en/rest/apps/installations?apiVersion=2022-11-28#list-repositories-accessible-to-the-user-access-token
        """
        per_page = 100

        def get_page(*, page):
            return requests.get(
                f"https://api.github.com/user/installations/{installation_id}/repositories",
                params={"per_page": per_page, "page": page},
                **self.github_request_kwargs,
            ).json()

        response = get_page(page=1)
        repos = [repo["full_name"] for repo in response["repositories"]]

        remaining_pages = (response["total_count"] - 1) // per_page

        for ii in range(remaining_pages):
            repos += [
                repo["full_name"]
                for repo in get_page(page=ii + 2)["repositories"]
            ]

        return repos

    def get_list(self):
        repos = []

        for installation in self.installations:
            repos += self.get_repos(installation_id=installation["id"])

        return repos
