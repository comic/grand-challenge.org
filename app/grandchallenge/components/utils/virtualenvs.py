import shlex
import subprocess
from pathlib import Path


def run_in_virtualenv(*, venv_location, command):
    """
    Runs a Python script as a subprocess in an existing isolated virtual environment.

    Returns the result of the process.
    """
    venv_activate_command = shlex.join(
        [
            "source",
            str(Path(venv_location).resolve() / "bin" / "activate"),
        ]
    )
    escaped_command = shlex.join(command)

    return subprocess.run(
        [
            "/bin/sh",
            "-c",
            f"{venv_activate_command} && {escaped_command}",
        ],
        env=None,
        text=True,
        check=True,
        capture_output=True,
    )
