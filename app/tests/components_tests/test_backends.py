import io
import json
import os
from zipfile import ZipInfo

import pytest
from django.template.defaultfilters import title

from grandchallenge.components.backends.docker_client import _get_cpuset_cpus
from grandchallenge.components.backends.utils import (
    _filter_members,
    user_error,
)
from grandchallenge.components.schemas import GPUTypeChoices
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.components_tests.resources.backends import IOCopyExecutor


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


@pytest.mark.django_db
def test_inputs_json(settings):
    executor = IOCopyExecutor(
        job_id="test-test-test",
        exec_image_repo_tag="test",
        memory_limit=4,
        time_limit=100,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
    )

    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(2)

    executor.provision(input_civs=[civ1, civ2], input_prefixes={})

    with io.BytesIO() as fileobj:
        executor._s3_client.download_fileobj(
            Fileobj=fileobj,
            Bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
            Key="/io/test/test/test/inputs.json",
        )
        fileobj.seek(0)
        result = json.loads(fileobj.read().decode("utf-8"))

    expected = [
        {
            "interface": {
                "title": civ1.interface.title,
                "description": civ1.interface.description,
                "slug": civ1.interface.slug,
                "kind": civ1.interface.get_kind_display(),
                "pk": civ1.interface.pk,
                "default_value": civ1.interface.default_value,
                "super_kind": title(civ1.interface.super_kind.name),
                "relative_path": civ1.interface.relative_path,
                "overlay_segments": civ1.interface.overlay_segments,
                "look_up_table": civ1.interface.look_up_table,
            },
            "value": civ1.value,
            "file": None,
            "image": civ1.image,
            "pk": civ1.pk,
        },
        {
            "interface": {
                "title": civ2.interface.title,
                "description": civ2.interface.description,
                "slug": civ2.interface.slug,
                "kind": civ2.interface.get_kind_display(),
                "pk": civ2.interface.pk,
                "default_value": civ2.interface.default_value,
                "super_kind": title(civ2.interface.super_kind.name),
                "relative_path": civ2.interface.relative_path,
                "overlay_segments": civ2.interface.overlay_segments,
                "look_up_table": civ2.interface.look_up_table,
            },
            "value": civ2.value,
            "file": None,
            "image": civ2.image,
            "pk": civ2.pk,
        },
    ]

    for e in expected:
        assert e in result
