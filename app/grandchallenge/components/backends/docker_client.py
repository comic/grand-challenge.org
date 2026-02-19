import json
import logging
import shlex
from subprocess import CalledProcessError, run

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from grandchallenge.components.registry import _get_registry_auth_config
from grandchallenge.evaluation.utils import get

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


def stop_container(*, name):
    try:
        container_id = get_container_id(name=name)
        return _run_docker_command("stop", container_id)
    except ObjectDoesNotExist:
        return


def remove_container(*, name):
    try:
        container_id = get_container_id(name=name)
        try:
            _run_docker_command("rm", container_id)
        except CalledProcessError as error:
            if "Error response from daemon: No such container" in error.stderr:
                raise ObjectDoesNotExist from error
            elif "Error: No such container" in error.stderr:
                # Old versions of docker return this error string
                raise ObjectDoesNotExist from error
            elif (
                f"Error response from daemon: removal of container {container_id} is already in progress"
                in error.stderr
            ):
                return
            else:
                raise
    except ObjectDoesNotExist:
        return


def get_container_id(*, name):
    result = _run_docker_command(
        "ps", "--all", "--quiet", "--filter", f"name={name}"
    )
    return get([line for line in result.stdout.splitlines()])


def inspect_container(*, name):
    container_id = get_container_id(name=name)
    result = _run_docker_command(
        "inspect", "--format", "{{json .}}", container_id
    )
    return json.loads(result.stdout)


def get_logs(*, name, tail=None):
    container_id = get_container_id(name=name)
    args = ["logs", "--timestamps"]

    if tail is not None:
        args.extend(["--tail", str(tail)])

    try:
        result = _run_docker_command(*args, container_id)
        return result.stdout.splitlines() + result.stderr.splitlines()
    except CalledProcessError as error:
        if (
            "error from daemon in stream: Error grabbing logs: invalid character"
            in error.stderr
        ):
            logger.error("Docker logs are corrupt", exc_info=True)
            return error.stdout.splitlines()
        else:
            raise error


def inspect_image(*, repo_tag):
    try:
        result = _run_docker_command(
            "image", "inspect", "--format", "{{json .}}", repo_tag
        )
        return json.loads(result.stdout)
    except CalledProcessError as error:
        if ": No such image" in error.stderr:
            raise ObjectDoesNotExist from error
        else:
            raise


def run_container(
    *,
    repo_tag,
    name,
    environment,
    ports,
    mem_limit,
):
    try:
        inspect_image(repo_tag=repo_tag)
    except ObjectDoesNotExist:
        pull_image(repo_tag=repo_tag, authenticate=True)

    docker_args = [
        "run",
        "--name",
        name,
        "--memory",
        f"{mem_limit}g",
        "--memory-swap",
        f"{mem_limit}g",
        "--cpu-period",
        str(settings.COMPONENTS_CPU_PERIOD),
        "--cpu-quota",
        str(settings.COMPONENTS_CPU_QUOTA),
        "--cpu-shares",
        str(settings.COMPONENTS_CPU_SHARES),
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        str(settings.COMPONENTS_PIDS_LIMIT),
        "--log-driver",
        "json-file",
        "--log-opt",
        "max-size=1g",
        "--platform",
        settings.COMPONENTS_CONTAINER_PLATFORM,
        "--init",
        "--rm",
        "--detach",
        "--cap-drop",
        "all",
    ]

    for k, v in environment.items():
        docker_args.extend(["--env", f"{k}={v}"])

    for port in ports:
        docker_args.extend(
            [
                "--publish",
                f"0.0.0.0::{port}",
            ]
        )

    # Last two args must be the repo tag and optional command
    docker_args.append(repo_tag)

    return _run_docker_command(*docker_args)
