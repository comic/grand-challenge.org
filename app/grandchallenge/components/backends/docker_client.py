import logging
import shlex
from subprocess import run

from django.conf import settings
from django.utils import timezone

from grandchallenge.components.registry import _get_registry_auth_config

logger = logging.getLogger(__name__)


def _run_docker_command(*args, authenticate=False):
    clean_command = shlex.join(["docker", *args])

    if authenticate:
        auth_config = _get_registry_auth_config()
        login_command = shlex.join(
            [
                "docker",
                "login",
                "--username",
                auth_config["username"],
                "--password",
                auth_config["password"],
                settings.COMPONENTS_REGISTRY_URL,
            ]
        )
        clean_command = f"{login_command} && {clean_command}"

    return run(
        ["/bin/sh", "-c", clean_command],
        check=True,
        capture_output=True,
        text=True,
    )


def pull_image(*, repo_tag, authenticate=False):
    return _run_docker_command(
        "image", "pull", repo_tag, authenticate=authenticate
    )


def build_image(*, repo_tag, path):
    return _run_docker_command(
        "build",
        "--build-arg",
        f"BUILD_TIME={timezone.now().isoformat()}",
        "--platform",
        settings.COMPONENTS_CONTAINER_PLATFORM,
        "--tag",
        repo_tag,
        path,
    )


def save_image(*, repo_tag, output):
    return _run_docker_command("save", "--output", str(output), repo_tag)
