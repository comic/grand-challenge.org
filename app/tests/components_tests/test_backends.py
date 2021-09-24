import os
from pathlib import Path

import pytest
from django.core.files.base import ContentFile

from grandchallenge.components.backends.docker import DockerConnection
from grandchallenge.components.backends.utils import user_error
from grandchallenge.components.models import InterfaceKindChoices
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.components_tests.stubs import AmazonECSExecutorStub
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
        memory_limit=4,
        requires_gpu=False,
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
            interface=interfaces[1],
            image=ImageFileFactory(
                file__from_path=Path(__file__).parent.parent
                / "algorithms_tests"
                / "resources"
                / "input_file.tif"
            ).image,
        ),
        ComponentInterfaceValueFactory(interface=interfaces[2]),
    ]
    civs[2].file.save("whatever.csv", ContentFile(b"foo,\nbar,\n"))

    settings.COMPONENTS_AMAZON_ECS_NFS_MOUNT_POINT = tmp_path

    executor = AmazonECSExecutorStub(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_sha256="",
        exec_image_repo_tag="",
        exec_image_file=None,
        memory_limit=4,
        requires_gpu=False,
    )

    executor.provision(input_civs=civs, input_prefixes={})
    executor.execute()
    executor.handle_event(
        event={
            "taskArn": "algorithms-job-00000000-0000-0000-0000-000000000000",
            "stopCode": "EssentialContainerExited",
        }
    )

    assert {str(f.relative_to(tmp_path)) for f in tmp_path.glob("**/*")} == {
        "algorithms",
        "algorithms/job",
        "algorithms/job/00000000-0000-0000-0000-000000000000",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/test.csv",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/test",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/test/bool.json",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/images",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/images/test-image",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/images/test-image/input_file.tif",
        "algorithms/job/00000000-0000-0000-0000-000000000000/output",
        "algorithms/job/00000000-0000-0000-0000-000000000000/output/metrics.json",
        "algorithms/job/00000000-0000-0000-0000-000000000000/output/results.json",
        "algorithms/job/00000000-0000-0000-0000-000000000000/output/test.csv",
        "algorithms/job/00000000-0000-0000-0000-000000000000/output/test",
        "algorithms/job/00000000-0000-0000-0000-000000000000/output/test/bool.json",
        "algorithms/job/00000000-0000-0000-0000-000000000000/output/images",
        "algorithms/job/00000000-0000-0000-0000-000000000000/output/images/test-image",
        "algorithms/job/00000000-0000-0000-0000-000000000000/output/images/test-image/input_file.tif",
    }

    # Exclude the CIV reading as this is unsupported
    outputs = executor.get_outputs(output_interfaces=interfaces[:2])
    assert len(outputs) == 2

    executor.deprovision()

    assert {str(f.relative_to(tmp_path)) for f in tmp_path.glob("**/*")} == {
        "algorithms",
        "algorithms/job",
    }


@pytest.mark.django_db
def test_input_prefixes(tmp_path, settings):
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
            interface=interfaces[1],
            image=ImageFileFactory(
                file__from_path=Path(__file__).parent.parent
                / "algorithms_tests"
                / "resources"
                / "input_file.tif"
            ).image,
        ),
        ComponentInterfaceValueFactory(interface=interfaces[2]),
    ]
    settings.COMPONENTS_AMAZON_ECS_NFS_MOUNT_POINT = tmp_path

    executor = AmazonECSExecutorStub(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_sha256="",
        exec_image_repo_tag="",
        exec_image_file=None,
        memory_limit=4,
        requires_gpu=False,
    )
    executor.provision(
        input_civs=civs,
        input_prefixes={
            str(civs[0].pk): "first/output/",
            str(civs[1].pk): "second/output",
        },
    )

    assert {str(f.relative_to(tmp_path)) for f in tmp_path.glob("**/*")} == {
        "algorithms",
        "algorithms/job",
        "algorithms/job/00000000-0000-0000-0000-000000000000",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/test.csv",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/first",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/first/output",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/first/output/test",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/first/output/test/bool.json",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/second",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/second/output",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/second/output/images",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/second/output/images/test-image",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/second/output/images/test-image/input_file.tif",
        "algorithms/job/00000000-0000-0000-0000-000000000000/output",
    }
