import os

import pytest
from django.core.files.base import ContentFile

from grandchallenge.components.backends.aws_batch import AWSBatchExecutor
from grandchallenge.components.backends.docker import (
    DockerConnection,
    user_error,
)
from grandchallenge.components.models import InterfaceKindChoices
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFileFactory


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

    c = DockerConnection(
        job_id="",
        exec_image_sha256="",
        exec_image_repo_tag="",
        exec_image_file=None,
    )

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


@pytest.mark.django_db
def test_provision(tmp_path, settings):
    interfaces = [
        ComponentInterfaceFactory(
            kind=InterfaceKindChoices.BOOL, relative_path="test/bool.json"
        ),
        ComponentInterfaceFactory(
            kind=InterfaceKindChoices.IMAGE, relative_path="images/test-image"
        ),
        ComponentInterfaceFactory(
            kind=InterfaceKindChoices.CSV, relative_path="test.csv"
        ),
    ]
    civs = [
        ComponentInterfaceValueFactory(interface=interfaces[0], value=True),
        ComponentInterfaceValueFactory(
            interface=interfaces[1], image=ImageFileFactory().image
        ),
        ComponentInterfaceValueFactory(interface=interfaces[2]),
    ]
    civs[2].file.save("whatever.csv", ContentFile(b"foo,\nbar,\n"))

    settings.COMPONENTS_AWS_BATCH_NFS_MOUNT_POINT = tmp_path

    executor = AWSBatchExecutor(
        job_id="foo-bar-12345-67890",
        exec_image_sha256="",
        exec_image_repo_tag="",
        exec_image_file="",
    )
    executor.provision(input_civs=civs, input_prefixes={})

    assert {str(f.relative_to(tmp_path)) for f in tmp_path.glob("**/*")} == {
        "foo",
        "foo/bar",
        "foo/bar/12345-67890",
        "foo/bar/12345-67890/input",
        "foo/bar/12345-67890/input/test.csv",
        "foo/bar/12345-67890/input/test",
        "foo/bar/12345-67890/input/test/bool.json",
        "foo/bar/12345-67890/input/images",
        "foo/bar/12345-67890/input/images/test-image",
        "foo/bar/12345-67890/input/images/test-image/example.dat",
        "foo/bar/12345-67890/output",
    }
