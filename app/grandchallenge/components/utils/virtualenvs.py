import subprocess
from pathlib import Path


def run_script_in_venv(*, venv_location, python_script, args=None):
    """
    Runs a Python script as a subprocess in an existing isolated virtual environment.

    Returns the result of the process.
    """
    venv_path_activate = Path(venv_location).resolve() / "bin" / "activate"
    python_script = Path(python_script).resolve()
    args = " ".join(args or [])

    command = f"source {venv_path_activate} && python {python_script} {args}"
    return subprocess.run(
        ["bash", "-c", command],
        env=None,
        text=True,
        check=True,
        capture_output=True,
    )
