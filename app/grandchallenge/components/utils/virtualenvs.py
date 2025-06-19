import shlex
import subprocess
from pathlib import Path


def run_script_in_venv(*, venv_location, python_script, args=None):
    """
    Runs a Python script as a subprocess in an existing isolated virtual environment.

    Returns the result of the process.
    """
    venv_activate = Path(venv_location).resolve() / "bin" / "activate"
    python_script = Path(python_script).resolve()

    venv_activate_command = shlex.join(
        [
            "source",
            str(venv_activate),
        ]
    )
    python_command = shlex.join(
        [
            "python",
            str(python_script),
            *args,
        ]
    )
    return subprocess.run(
        [
            "bash",
            "-c",
            f"{venv_activate_command} && {python_command}",
        ],
        env=None,
        text=True,
        check=True,
        capture_output=True,
    )
