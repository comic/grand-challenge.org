import os
from zipfile import ZipInfo

import pytest

from grandchallenge.components.backends.docker_client import _get_cpuset_cpus
from grandchallenge.components.backends.utils import (
    _filter_members,
    user_error,
)
from grandchallenge.components.models import GPUTypeChoices
from tests.components_tests.resources.backends import InsecureDockerExecutor


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

    assert os.cpu_count() > 1
    assert _get_cpuset_cpus() == expected


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


def test_internal_logs_filtered():
    logs = '2022-05-31T09:47:57.371317000Z {"log": "Found credentials in environment variables.", "level": "INFO", "source": "stdout", "internal": true, "task": null}\n2022-05-31T09:47:57.478222400Z {"log": "Downloading self.bucket_key=\'/evaluation/evaluation/9b966b3f-3fa2-42f2-a9ae-8457565f9644/predictions.zip\' from self.bucket_name=\'grand-challenge-components-inputs\' to dest_file=PosixPath(\'/input/predictions.zip\')", "level": "INFO", "source": "stdout", "internal": true, "task": null}\n2022-05-31T09:47:57.503693300Z {"log": "Extracting member[\'src\']=\'submission/submission.csv\' from /tmp/tmpfsxjvtow/src.zip to /input/submission.csv", "level": "INFO", "source": "stdout", "internal": true, "task": null}\n2022-05-31T09:47:57.504206200Z {"log": "Extracting member[\'src\']=\'submission/images/image10x10x10.mhd\' from /tmp/tmpfsxjvtow/src.zip to /input/images/image10x10x10.mhd", "level": "INFO", "source": "stdout", "internal": true, "task": null}\n2022-05-31T09:47:57.504533600Z {"log": "Extracting member[\'src\']=\'submission/images/image10x10x10.zraw\' from /tmp/tmpfsxjvtow/src.zip to /input/images/image10x10x10.zraw", "level": "INFO", "source": "stdout", "internal": true, "task": null}\n2022-05-31T09:48:03.205773000Z {"log": "Greetings from stdout", "level": "INFO", "source": "stdout", "internal": false, "task": "evaluation-evaluation-9b966b3f-3fa2-42f2-a9ae-8457565f9644"}\n2022-05-31T09:48:03.218474800Z {"log": "Uploading src_file=\'/output/metrics.json\' to self.bucket_name=\'grand-challenge-components-outputs\' with self.bucket_key=\'evaluation/evaluation/9b966b3f-3fa2-42f2-a9ae-8457565f9644/metrics.json\'", "level": "INFO", "source": "stdout", "internal": true, "task": null}\n'

    executor = InsecureDockerExecutor(
        job_id="test",
        exec_image_repo_tag="test",
        memory_limit=4,
        time_limit=100,
        requires_gpu=False,
        desired_gpu_type=GPUTypeChoices.T4,
    )
    executor._parse_loglines(loglines=logs.splitlines())

    assert (
        executor.stdout
        == "2022-05-31T09:48:03.205773000Z Greetings from stdout"
    )
