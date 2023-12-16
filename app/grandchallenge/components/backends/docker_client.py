import json
import os
import shlex
from subprocess import CalledProcessError, run

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.components.registry import _get_registry_auth_config
from grandchallenge.evaluation.utils import get


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
        "--platform",
        settings.COMPONENTS_CONTAINER_PLATFORM,
        "--tag",
        repo_tag,
        path,
    )


def save_image(*, repo_tag, output):
    return _run_docker_command("save", "--output", str(output), repo_tag)


def load_image(*, input):
    return _run_docker_command("load", "--input", str(input))


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


def inspect_network(*, name):
    result = _run_docker_command(
        "network", "inspect", "--format", "{{json .}}", name
    )
    return json.loads(result.stdout)


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
            if "Error: No such container" in error.stderr:
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

    result = _run_docker_command(*args, container_id)

    return result.stdout.splitlines() + result.stderr.splitlines()


def run_container(  # noqa: C901
    *,
    repo_tag,
    name,
    labels,
    environment,
    network,
    mem_limit,
    ports=None,
    extra_hosts=None,
    command=None,
    remove=False,
    detach=True,
):
    docker_args = [
        "run",
        "--name",
        name,
        "--network",
        network,
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
        "--cpuset-cpus",
        _get_cpuset_cpus(),
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
    ]

    if detach:
        docker_args.append("--detach")

    if remove:
        docker_args.append("--rm")

    if not settings.COMPONENTS_DOCKER_KEEP_CAPS_UNSAFE:
        docker_args.extend(["--cap-drop", "all"])

    if settings.COMPONENTS_DOCKER_RUNTIME is not None:
        docker_args.extend(["--runtime", settings.COMPONENTS_DOCKER_RUNTIME])

    for k, v in labels.items():
        docker_args.extend(["--label", f"{k}={v}"])

    for k, v in environment.items():
        docker_args.extend(["--env", f"{k}={v}"])

    if extra_hosts is not None:
        for k, v in extra_hosts.items():
            docker_args.extend(["--add-host", f"{k}:{v}"])

    if ports is not None:
        for container_port, v in ports.items():
            bind_address, host_port = v
            host_port = "" if host_port is None else host_port
            docker_args.extend(
                [
                    "--publish",
                    f"{bind_address}:{host_port}:{container_port}",
                ]
            )

    # Last two args must be the repo tag and optional command
    docker_args.append(repo_tag)
    if command is not None:
        docker_args.extend(command)

    return _run_docker_command(*docker_args)


def _get_cpuset_cpus():
    """
    The cpuset_cpus as a string.

    Returns
    -------
        The setting COMPONENTS_CPUSET_CPUS if this is set to a
        none-empty string. Otherwise, works out the available cpu
        from the os.
    """
    if settings.COMPONENTS_CPUSET_CPUS:
        return settings.COMPONENTS_CPUSET_CPUS
    else:
        # Get the cpu count, note that this is setting up the container
        # so that it can use all of the CPUs on the system. To limit
        # the containers execution set COMPONENTS_CPUSET_CPUS
        # externally.
        cpus = os.cpu_count()
        if cpus in [None, 1]:
            return "0"
        else:
            return f"0-{cpus - 1}"
