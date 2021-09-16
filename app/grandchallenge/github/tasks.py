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


def get_repo_url(payload):
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

    repo_url = payload["repository"]["html_url"]
    return repo_url.replace("//", f"//x-access-token:{access_token}@")


@shared_task()
def get_zipfile(*, pk):
    GitHubWebhookMessage = apps.get_model(  # noqa: N806
        app_label="github", model_name="GitHubWebhookMessage"
    )
    ghwm = GitHubWebhookMessage.objects.get(pk=pk)
    payload = ghwm.payload
    repo_url = get_repo_url(payload)
    zip_name = f"{ghwm.repo_name}-{ghwm.tag}.zip"
    tmp_zip = tempfile.NamedTemporaryFile()
    has_open_source_license = False
    license = "No license file found"
    try:
        recurse_submodules = Algorithm.objects.get(
            repo_name=ghwm.payload["repository"]["full_name"]
        ).recurse_submodules

    except Algorithm.DoesNotExist:
        recurse_submodules = False
    with tempfile.TemporaryDirectory() as tmpdirname:
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
        try:
            process = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as err:
            ghwm.error = str(err)
            ghwm.save()
            raise

        process = subprocess.Popen(
            ["licensee", tmpdirname], stdout=subprocess.PIPE
        )
        process.wait()
        output = process.stdout.read()
        regex_license = re.compile(r"License: (?P<license>.*)?$", re.M)
        match = regex_license.search(output.decode("utf-8"))
        if match:
            license = match.group("license")
            if license in settings.OPEN_SOURCE_LICENSES:
                has_open_source_license = True
        with zipfile.ZipFile(tmp_zip.name, "w") as zipf:
            for foldername, _subfolders, filenames in os.walk(tmpdirname):
                for filename in filenames:
                    file_path = os.path.join(foldername, filename)
                    zipf.write(
                        file_path, file_path.replace(f"{tmpdirname}/", "")
                    )
        temp_file = files.File(tmp_zip, name=zip_name,)
        ghwm.zipfile = temp_file
        ghwm.has_open_source_license = has_open_source_license
        ghwm.license_check_result = license
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
        Algorithm.objects.filter(repo_name=repo["full_name"]).update(
            repo_name=""
        )
