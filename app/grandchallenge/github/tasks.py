import base64
import json
import os
import subprocess
import tempfile
import zipfile
from datetime import timedelta

import jwt
import requests
from celery.utils.log import get_task_logger
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from django.conf import settings
from django.core import files
from django.db import transaction
from django.db.transaction import on_commit
from django.utils.timezone import now

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.codebuild.tasks import create_codebuild_build
from grandchallenge.core.celery import (
    acks_late_2xlarge_task,
    acks_late_micro_short_task,
)
from grandchallenge.github.exceptions import GitHubBadRefreshTokenException

logger = get_task_logger(__name__)


def get_repo_url(payload):
    installation_id = payload["installation"]["id"]
    b64_key = settings.GITHUB_PRIVATE_KEY_BASE64
    b64_bytes = b64_key.encode("ascii")
    key_bytes = base64.b64decode(b64_bytes)
    private_key = serialization.load_pem_private_key(
        key_bytes, password=None, backend=default_backend()
    )
    current_time = now()
    msg = {
        "iat": int(current_time.timestamp()) - 60,
        "exp": int(current_time.timestamp()) + 60 * 5,
        "iss": settings.GITHUB_APP_ID,
    }
    token = jwt.encode(msg, private_key, algorithm="RS256")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    resp = requests.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers=headers,
        timeout=10,
    )
    access_token = json.loads(resp.content)["token"]

    repo_url = payload["repository"]["html_url"]
    return repo_url.replace("//", f"//x-access-token:{access_token}@")


def install_lfs():
    process = subprocess.check_output(
        ["git", "lfs", "install"], stderr=subprocess.STDOUT
    )
    return process


def fetch_repo(payload, repo_url, tmpdirname, recurse_submodules):
    cmd = [
        "git",
        "clone",
        "--branch",
        payload["ref"],
        "--depth",
        "1",
        repo_url,
        tmpdirname,
    ]
    if recurse_submodules:
        cmd.insert(2, "--recurse-submodules")

    process = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    return process


def check_license(tmpdirname):
    process = subprocess.Popen(
        ["licensee", "detect", tmpdirname, "--json", "--no-remote"],
        stdout=subprocess.PIPE,
    )
    try:
        outs, errs = process.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        raise

    return json.loads(outs.decode("utf-8"))


def save_zipfile(ghwm, tmpdirname):
    zip_name = f"{ghwm.repo_name}-{ghwm.tag}.zip"
    tmp_zip = tempfile.NamedTemporaryFile()
    with zipfile.ZipFile(tmp_zip.name, "w") as zipf:
        for foldername, _subfolders, filenames in os.walk(tmpdirname):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                zipf.write(file_path, file_path.replace(f"{tmpdirname}/", ""))
    temp_file = files.File(tmp_zip, name=zip_name)
    return temp_file


def build_repo(ghwm_pk):
    on_commit(
        create_codebuild_build.signature(kwargs={"pk": ghwm_pk}).apply_async
    )


@acks_late_2xlarge_task
def get_zipfile(*, pk):
    from grandchallenge.github.models import GitHubWebhookMessage

    ghwm = GitHubWebhookMessage.objects.get(pk=pk)

    if ghwm.clone_status != GitHubWebhookMessage.CloneStatusChoices.PENDING:
        raise RuntimeError("Clone status was not pending")

    payload = ghwm.payload
    repo_url = get_repo_url(payload)
    ghwm.clone_status = GitHubWebhookMessage.CloneStatusChoices.STARTED
    ghwm.save()

    try:
        recurse_submodules = Algorithm.objects.get(
            repo_name=ghwm.payload["repository"]["full_name"]
        ).recurse_submodules
    except Algorithm.DoesNotExist:
        logger.info("No algorithm linked to this repo")
        ghwm.clone_status = (
            GitHubWebhookMessage.CloneStatusChoices.NOT_APPLICABLE
        )
        ghwm.save()
        return

    with tempfile.TemporaryDirectory() as tmpdirname:
        try:
            # Run git lfs install here, doing it in the dockerfile does not
            # seem to work
            install_lfs()
            fetch_repo(payload, repo_url, tmpdirname, recurse_submodules)
            license_check_result = check_license(tmpdirname)
            temp_file = save_zipfile(ghwm, tmpdirname)

            # update GithubWebhook object
            ghwm.zipfile = temp_file
            ghwm.license_check_result = license_check_result
            ghwm.clone_status = GitHubWebhookMessage.CloneStatusChoices.SUCCESS
            ghwm.save()

            build_repo(ghwm.pk)

        except Exception as e:
            ghwm.stdout = str(getattr(e, "stdout", ""))
            ghwm.stderr = str(getattr(e, "stderr", ""))
            ghwm.clone_status = GitHubWebhookMessage.CloneStatusChoices.FAILURE
            ghwm.save()

            if not ghwm.user_error:
                raise


@acks_late_micro_short_task
def unlink_algorithm(*, pk):
    from grandchallenge.github.models import GitHubWebhookMessage

    ghwm = GitHubWebhookMessage.objects.get(pk=pk)
    for repo in ghwm.payload["repositories"]:
        Algorithm.objects.filter(repo_name=repo["full_name"]).update(
            repo_name=""
        )


@acks_late_micro_short_task
@transaction.atomic
def cleanup_expired_tokens():
    from grandchallenge.github.models import GitHubUserToken

    GitHubUserToken.objects.filter(refresh_token_expires__lt=now()).only(
        "pk"
    ).delete()


@acks_late_micro_short_task
def refresh_user_token(*, pk):
    from grandchallenge.github.models import GitHubUserToken

    token = GitHubUserToken.objects.get(pk=pk)

    try:
        token.refresh_access_token()
    except GitHubBadRefreshTokenException:
        token.delete()
        return

    token.save()


@acks_late_micro_short_task
def refresh_expiring_user_tokens():
    """Refresh user tokens expiring in the next 1 to 28 days"""
    from grandchallenge.github.models import GitHubUserToken

    queryset = GitHubUserToken.objects.filter(
        refresh_token_expires__gt=now() + timedelta(days=1),
        refresh_token_expires__lt=now() + timedelta(days=28),
    )
    for token in queryset.iterator():
        on_commit(
            refresh_user_token.signature(kwargs={"pk": token.pk}).apply_async
        )
