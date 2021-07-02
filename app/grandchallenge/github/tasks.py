import base64
import json
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
from django.core.files.temp import NamedTemporaryFile
from django.db.transaction import on_commit

from grandchallenge.codebuild.tasks import create_algorithm_image
from grandchallenge.codebuild.utils import get_buildspec_path


def get_buildspec_zip(*, zfile, algorithm_name, output_path):
    with zipfile.ZipFile(zfile, "a") as zipf:
        folder_name = zipf.filelist[0].filename
        source_path = get_buildspec_path(
            algorithm_name=algorithm_name,
            folder_name=folder_name,
            output_path=output_path,
        )
        destination = "buildspec.yml"
        zipf.write(source_path, destination)
    return zfile


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
    full_name = payload["repository"]["full_name"]
    headers["Authorization"] = f"token {access_token}"
    zipfile_url = (
        f"https://api.github.com/repos/{full_name}/zipball/{payload['ref']}"
    )
    with requests.get(
        zipfile_url, headers=headers, timeout=10, stream=True
    ) as file:
        with NamedTemporaryFile(delete=True) as tmp_file:
            with open(tmp_file.name, "wb") as fd:
                for chunk in file.iter_content(chunk_size=128):
                    fd.write(chunk)

            tmp_file.flush()
            import ipdb

            ipdb.set_trace()
            zfile = get_buildspec_zip(
                zfile=tmp_file,
                algorithm_name=ghwm.project_name,
                output_path=ghwm.output_path,
            )
            temp_file = files.File(zfile, name=f"{ghwm.project_name}.zip",)

            ghwm.zipfile = temp_file
            ghwm.save()

    on_commit(
        lambda: create_algorithm_image.apply_async(kwargs={"pk": ghwm.pk})
    )
