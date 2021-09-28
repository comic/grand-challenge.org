import datetime
import os
from pathlib import Path
from zipfile import ZipInfo

import pytest
from django.core.files.base import ContentFile, File

from grandchallenge.components.backends.docker import DockerConnection
from grandchallenge.components.backends.exceptions import (
    TaskCancelled,
    TaskStillExecuting,
)
from grandchallenge.components.backends.utils import (
    _filter_members,
    user_error,
)
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
        ("", f"0-{os.cpu_count() - 1}"),
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
            # Minimal successful event
            "taskDefinitionArn": "arn:aws:ecs:region:123456789012:task-definition/algorithms-job-00000000-0000-0000-0000-000000000000:1",
            "group": "components-gpu",
            "stopCode": "EssentialContainerExited",
            "containers": [
                {
                    "exitCode": 143,
                    "name": "algorithms-job-00000000-0000-0000-0000-000000000000-timeout",
                },
                {
                    "exitCode": 0,
                    "name": "algorithms-job-00000000-0000-0000-0000-000000000000",
                },
            ],
            "startedAt": "2021-09-25T10:50:24.248Z",
            "stoppedAt": "2021-09-25T11:02:30.776Z",
        }
    )

    assert executor.duration == datetime.timedelta(
        seconds=726, microseconds=528000
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


@pytest.mark.django_db
def test_ecs_unzip(tmp_path, settings, submission_file):
    interface = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ZIP, relative_path="preds.zip"
    )
    civ = ComponentInterfaceValueFactory(interface=interface)

    with open(submission_file, "rb") as f:
        civ.file.save("my_submission.zip", File(f))

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
        input_civs=[civ], input_prefixes={},
    )

    assert {str(f.relative_to(tmp_path)) for f in tmp_path.glob("**/*")} == {
        "algorithms",
        "algorithms/job",
        "algorithms/job/00000000-0000-0000-0000-000000000000",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/submission.csv",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/images",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/images/image10x10x10.mhd",
        "algorithms/job/00000000-0000-0000-0000-000000000000/input/images/image10x10x10.zraw",
        "algorithms/job/00000000-0000-0000-0000-000000000000/output",
    }


def test_filter_members():
    members = _filter_members(
        [
            ZipInfo("__MACOSX/foo"),
            ZipInfo("submission/submission.csv"),
            ZipInfo("submission/__MACOSX/bar"),
            ZipInfo("baz/.DS_Store"),
            ZipInfo("submission/images/image10x10x10.mhd"),
            ZipInfo("submission/images/image10x10x10.zraw"),
        ]
    )
    assert members == [
        {"src": "submission/submission.csv", "dest": "submission.csv"},
        {
            "src": "submission/images/image10x10x10.mhd",
            "dest": "images/image10x10x10.mhd",
        },
        {
            "src": "submission/images/image10x10x10.zraw",
            "dest": "images/image10x10x10.zraw",
        },
    ]


def test_filter_members_no_prefix():
    members = _filter_members(
        [
            ZipInfo("__MACOSX/foo"),
            ZipInfo("submi1ssion/submission.csv"),
            ZipInfo("submi2ssion/__MACOSX/bar"),
            ZipInfo("baz/.DS_Store"),
            ZipInfo("submi3ssion/images/image10x10x10.mhd"),
            ZipInfo("submission/images/image10x10x10.zraw"),
        ]
    )
    assert members == [
        {
            "src": "submi1ssion/submission.csv",
            "dest": "submi1ssion/submission.csv",
        },
        {
            "src": "submi3ssion/images/image10x10x10.mhd",
            "dest": "submi3ssion/images/image10x10x10.mhd",
        },
        {
            "src": "submission/images/image10x10x10.zraw",
            "dest": "submission/images/image10x10x10.zraw",
        },
    ]


def test_filter_members_single_file():
    members = _filter_members([ZipInfo("foo")])
    assert members == [{"src": "foo", "dest": "foo"}]


def test_filter_members_single_file_nested():
    members = _filter_members([ZipInfo("foo/bar")])
    assert members == [{"src": "foo/bar", "dest": "bar"}]


def test_handle_stopped_successful_task():
    executor = AmazonECSExecutorStub(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_sha256="",
        exec_image_repo_tag="",
        exec_image_file=None,
        memory_limit=4,
        requires_gpu=False,
    )
    event = {
        "taskDefinitionArn": "arn:aws:ecs:region:123456789012:task-definition/algorithms-job-00000000-0000-0000-0000-000000000000:1",
        "group": "components-gpu",
        "stopCode": "EssentialContainerExited",
        "containers": [
            {
                "exitCode": 143,
                "name": "algorithms-job-00000000-0000-0000-0000-000000000000-timeout",
            },
            {
                "exitCode": 0,
                "name": "algorithms-job-00000000-0000-0000-0000-000000000000",
            },
        ],
        "startedAt": "2021-09-25T10:50:24.248Z",
        "stoppedAt": "2021-09-25T11:02:30.776Z",
    }
    assert executor._get_container_exit_codes(event=event) == {
        "algorithms-job-00000000-0000-0000-0000-000000000000": 0,
        "algorithms-job-00000000-0000-0000-0000-000000000000-timeout": 143,
    }


def test_handle_stopped_successful_fast_task():
    executor = AmazonECSExecutorStub(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_sha256="",
        exec_image_repo_tag="",
        exec_image_file=None,
        memory_limit=4,
        requires_gpu=False,
    )
    event = {
        "taskDefinitionArn": "arn:aws:ecs:region:123456789012:task-definition/algorithms-job-00000000-0000-0000-0000-000000000000:1",
        "group": "components-gpu",
        "stopCode": "TaskFailedToStart",  # as not all container had time to start
        "containers": [
            {
                # No container exit in this case
                "name": "algorithms-job-00000000-0000-0000-0000-000000000000-timeout",
            },
            {
                "exitCode": 0,
                "name": "algorithms-job-00000000-0000-0000-0000-000000000000",
            },
        ],
        "createdAt": "2021-09-25T10:50:24.248Z",  # No startedAt in this case
        "stoppedAt": "2021-09-25T11:02:30.776Z",
    }

    assert executor._get_container_exit_codes(event=event) == {
        "algorithms-job-00000000-0000-0000-0000-000000000000": 0
    }


def test_handle_stopped_start_failed_task():
    executor = AmazonECSExecutorStub(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_sha256="",
        exec_image_repo_tag="",
        exec_image_file=None,
        memory_limit=4,
        requires_gpu=False,
    )
    event = {
        "taskDefinitionArn": "arn:aws:ecs:region:123456789012:task-definition/algorithms-job-00000000-0000-0000-0000-000000000000:1",
        "group": "components-gpu",
        "stopCode": "TaskFailedToStart",
        "containers": [
            {
                # No container exit in this case
                "name": "algorithms-job-00000000-0000-0000-0000-000000000000-timeout",
            },
            {
                # No container exit in this case
                "name": "algorithms-job-00000000-0000-0000-0000-000000000000",
            },
        ],
        "createdAt": "2021-09-25T10:50:24.248Z",  # No startedAt in this case
        "stoppedAt": "2021-09-25T11:02:30.776Z",
    }

    with pytest.raises(TaskStillExecuting):
        # Task should be retried
        executor._get_container_exit_codes(event=event)


def test_handle_stopped_terminated_task():
    executor = AmazonECSExecutorStub(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_sha256="",
        exec_image_repo_tag="",
        exec_image_file=None,
        memory_limit=4,
        requires_gpu=False,
    )
    event = {
        "taskDefinitionArn": "arn:aws:ecs:region:123456789012:task-definition/algorithms-job-00000000-0000-0000-0000-000000000000:1",
        "group": "components-gpu",
        "stopCode": "TerminationNotice",
        "containers": [
            {
                # No container exit in this case
                "name": "algorithms-job-00000000-0000-0000-0000-000000000000-timeout",
            },
            {
                # No container exit in this case
                "name": "algorithms-job-00000000-0000-0000-0000-000000000000",
            },
        ],
        "createdAt": "2021-09-25T10:50:24.248Z",  # No startedAt in this case
        "stoppedAt": "2021-09-25T11:02:30.776Z",
    }

    with pytest.raises(TaskStillExecuting):
        # Task should be retried
        executor._get_container_exit_codes(event=event)


def test_handle_stopped_cancelled_task():
    executor = AmazonECSExecutorStub(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_sha256="",
        exec_image_repo_tag="",
        exec_image_file=None,
        memory_limit=4,
        requires_gpu=False,
    )
    event = {
        "taskDefinitionArn": "arn:aws:ecs:region:123456789012:task-definition/algorithms-job-00000000-0000-0000-0000-000000000000:1",
        "group": "components-gpu",
        "stopCode": "UserInitiated",
        "containers": [
            {
                # No container exit in this case
                "name": "algorithms-job-00000000-0000-0000-0000-000000000000-timeout",
            },
            {
                # No container exit in this case
                "name": "algorithms-job-00000000-0000-0000-0000-000000000000",
            },
        ],
        "createdAt": "2021-09-25T10:50:24.248Z",  # No startedAt in this case
        "stoppedAt": "2021-09-25T11:02:30.776Z",
    }

    with pytest.raises(TaskCancelled):
        # Task should be retried
        executor._get_container_exit_codes(event=event)


def test_set_duration_success():
    executor = AmazonECSExecutorStub(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_sha256="",
        exec_image_repo_tag="",
        exec_image_file=None,
        memory_limit=4,
        requires_gpu=False,
    )
    executor._set_duration(
        event={
            "createdAt": "2021-09-25T10:50:24.248Z",
            "startedAt": "2021-09-25T10:55:24.248Z",
            "stoppedAt": "2021-09-25T11:02:30.776Z",
        }
    )
    assert executor.duration == datetime.timedelta(
        seconds=426, microseconds=528000
    )


def test_set_duration_fast_task():
    executor = AmazonECSExecutorStub(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_sha256="",
        exec_image_repo_tag="",
        exec_image_file=None,
        memory_limit=4,
        requires_gpu=False,
    )
    executor._set_duration(
        event={
            "createdAt": "2021-09-25T10:50:24.248Z",
            "stoppedAt": "2021-09-25T11:02:30.776Z",
        }
    )
    assert executor.duration == datetime.timedelta(
        seconds=726, microseconds=528000
    )
