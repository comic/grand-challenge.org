import os

import pytest

from grandchallenge.container_exec.backends.docker import DockerConnection


@pytest.mark.django_db
@pytest.mark.parametrize(
    "cpuset,expected",
    (
        ("", f"0-{os.cpu_count()-1}"),
        ("0", "0"),
        ("1-3", "1-3"),
        ("1,2", "1,2"),
    ),
)
def test_cpuset_cpus(settings, cpuset, expected):
    settings.CONTAINER_EXEC_CPUSET_CPUS = cpuset

    c = DockerConnection(
        job_id="", job_model="", exec_image=None, exec_image_sha256=""
    )

    assert os.cpu_count() > 1
    assert c._run_kwargs["cpuset_cpus"] == expected
