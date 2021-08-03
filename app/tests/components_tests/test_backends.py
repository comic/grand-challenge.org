import os

import pytest

from grandchallenge.components.backends.docker import (
    DockerConnection,
    user_error,
)


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
    settings.COMPONENTS_CPUSET_CPUS = cpuset

    c = DockerConnection(job_id="", exec_image=None, exec_image_sha256="",)

    assert os.cpu_count() > 1
    assert c._run_kwargs["cpuset_cpus"] == expected


@pytest.mark.parametrize("with_timestamp", (True, False))
def test_user_error(with_timestamp):
    if with_timestamp:
        timestamp = "2020-11-22T07:19:38.976408700Z"
    else:
        timestamp = ""

    assert user_error(obj=f"{timestamp}foo\n") == "foo"
    assert user_error(obj=f"{timestamp}foo") == "foo"
    assert user_error(obj=f"{timestamp}foo\n\n") == "foo"
    assert user_error(obj=f"{timestamp}foo\n{timestamp}bar") == "bar"
    assert user_error(obj=f"{timestamp}foo\n{timestamp}bar\n\n") == "bar"
    assert user_error(obj=f"{timestamp}foo\n{timestamp}    a b\n\n") == "a b"
    assert user_error(obj=f"{timestamp}foo\nbar\n\n") == "bar"
    assert (
        user_error(obj=f"{timestamp}\n")
        == "No errors were reported in the logs."
    )
    assert (
        user_error(obj=f"{timestamp}\n{timestamp}\n")
        == "No errors were reported in the logs."
    )
