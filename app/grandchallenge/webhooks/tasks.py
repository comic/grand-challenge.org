import json
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


@shared_task()
def get_tarball(*, pk):
    GitHubWebhookMessage = apps.get_model(  # noqa: N806
        app_label="webhooks", model_name="GitHubWebhookMessage"
    )
    ghwm = GitHubWebhookMessage.objects.get(pk=pk)
    payload = ghwm.payload
    installation_id = payload["installation"]["id"]
    with open(settings.GITHUB_PRIVATE_KEY_PATH, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(), password=None, backend=default_backend()
        )
    now = datetime.now()
    msg = {
        "iat": int(now.timestamp()) - 60,
        "exp": int(now.timestamp()) + 60 * 10,
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
    )
    access_token = json.loads(resp.content)["token"]
    full_name = payload["repository"]["full_name"]
    headers["Authorization"] = f"token {access_token}"
    tarball_url = (
        f"https://api.github.com/repos/{full_name}/tarball/{payload['ref']}"
    )
    with requests.get(tarball_url, headers=headers, stream=True) as file:
        with NamedTemporaryFile(delete=True) as tmp_file:
            with open(tmp_file.name, "wb") as fd:
                for chunk in file.iter_content(chunk_size=128):
                    fd.write(chunk)

            tmp_file.flush()
            temp_file = files.File(
                tmp_file,
                name=f"{full_name.replace('/', '-')}-{payload['ref']}.tar",
            )

            ghwm.tarball = temp_file
            ghwm.save()
