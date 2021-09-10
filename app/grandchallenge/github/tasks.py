import base64
import json
import os
import re
import subprocess
import tempfile
import zipfile
from datetime import datetime

import jwt
import requests
from celery import shared_task
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from django.apps import apps
from django.conf import settings
from django.core import files
from django.db.transaction import on_commit

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.codebuild.tasks import create_codebuild_build


@shared_task()
def get_zipfile(*, pk):
    GitHubWebhookMessage = apps.get_model(  # noqa: N806
        app_label="github", model_name="GitHubWebhookMessage"
    )
    ghwm = GitHubWebhookMessage.objects.get(pk=pk)
    payload = ghwm.payload
    installation_id = payload["installation"]["id"]
    b64_key = settings.GITHUB_PRIVATE_KEY_BASE64
    b64_bytes = b64_key.encode("ascii")
    key_bytes = base64.b64decode(b64_bytes)
    private_key = serialization.load_pem_private_key(
        key_bytes, password=None, backend=default_backend()
    )
    now = datetime.now()
    msg = {
        "iat": int(now.timestamp()) - 60,
        "exp": int(now.timestamp()) + 60 * 5,
        "iss": settings.GITHUB_APP_ID,
    }
    token = jwt.encode(msg, private_key, algorithm="RS256")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    resp = requests.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers=headers,
        timeout=10,
    )
    access_token = json.loads(resp.content)["token"]
    headers["Authorization"] = f"token {access_token}"

    repo_url = payload["repository"]["html_url"]
    repo_url = repo_url.replace("//", f"//x-access-token:{access_token}@")
    zip_name = f"{ghwm.repo_name}-{ghwm.tag}.zip"
    tmp_zip = tempfile.NamedTemporaryFile()
    with tempfile.TemporaryDirectory() as tmpdirname:
        proces = subprocess.Popen(["git", "clone", "--recurse-submodules", "--branch",
                                  payload['ref'], "--depth", "1", repo_url, tmpdirname])
        proces.wait()
        with zipfile.ZipFile(tmp_zip.name, 'w') as zipf:
            for foldername, subfolders, filenames in os.walk(tmpdirname):
                for filename in filenames:
                    file_path = os.path.join(foldername, filename)
                    zipf.write(file_path, os.path.basename(file_path))
        temp_file = files.File(
            tmp_zip, name=zip_name,
        )
        ghwm.zipfile = temp_file
        ghwm.save()
    on_commit(
        lambda: create_codebuild_build.apply_async(kwargs={"pk": ghwm.pk})
    )


@shared_task
def unlink_algorithm(*, pk):
    GitHubWebhookMessage = apps.get_model(  # noqa: N806
        app_label="github", model_name="GitHubWebhookMessage"
    )
    ghwm = GitHubWebhookMessage.objects.get(pk=pk)
    for repo in ghwm.payload["repositories"]:
        Algorithm.objects.filter(
            repo_name=repo["full_name"]
        ).update(repo_name="")
