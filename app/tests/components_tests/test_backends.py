import asyncio
import hashlib
import hmac
import io
import json
import os
from datetime import timedelta
from unittest.mock import Mock
from uuid import uuid4
from zipfile import ZipInfo

import aioboto3
import botocore
import pytest
from botocore.auth import SigV4Auth
from django.core.exceptions import SuspiciousFileOperation
from django.template.defaultfilters import title

from grandchallenge.components.backends.base import (
    ASYNC_BOTO_CONFIG,
    ASYNC_CONCURRENCY,
    InferenceResult,
    s3_stream_response,
)
from grandchallenge.components.backends.docker_client import _get_cpuset_cpus
from grandchallenge.components.backends.exceptions import ComponentException
from grandchallenge.components.backends.utils import (
    _filter_members,
    user_error,
)
from grandchallenge.components.models import InterfaceKindChoices
from grandchallenge.components.schemas import GPUTypeChoices
from tests.cases_tests.factories import DICOMImageSetFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.components_tests.resources.backends import IOCopyExecutor
from tests.factories import ImageFactory, ImageFileFactory


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
    job_pk = uuid4()

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        time_limit=100,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
    )

    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(
        2, interface__kind=InterfaceKindChoices.ANY
    )

    executor.provision(input_civs=[civ1, civ2], input_prefixes={})

    with io.BytesIO() as fileobj:
        executor._s3_client.download_fileobj(
            Fileobj=fileobj,
            Bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
            Key=f"io/test/test/{job_pk}/inputs.json",
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


@pytest.mark.django_db
def test_invocation_json(settings):
    job_pk = uuid4()

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        time_limit=100,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
    )

    image_interface = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.PANIMG_IMAGE,
        relative_path="images/test",
    )
    file_interface = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY,
        relative_path="file.json",
        store_in_database=False,
    )
    value_interface = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY,
        relative_path="value.json",
        store_in_database=True,
    )

    image_civ = image_interface.create_instance(image=ImageFileFactory().image)
    file_civ = file_interface.create_instance(value=1337)
    value_civ = value_interface.create_instance(value="foo")
    prefixed_image_civ = image_interface.create_instance(
        image=ImageFileFactory().image
    )
    prefixed_file_civ = file_interface.create_instance(value=1337)
    prefixed_value_civ = value_interface.create_instance(value="foo")

    executor.provision(
        input_civs=[
            image_civ,
            file_civ,
            value_civ,
            prefixed_image_civ,
            prefixed_file_civ,
            prefixed_value_civ,
        ],
        input_prefixes={
            str(prefixed_image_civ.pk): "prefix/1",
            str(prefixed_file_civ.pk): "prefix/2",
            str(prefixed_value_civ.pk): "prefix/3",
        },
    )

    response = executor._s3_client.list_objects_v2(
        Bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
        Prefix=f"io/test/test/{job_pk}",
    )

    assert {content["Key"] for content in response["Contents"]} == {
        f"io/test/test/{job_pk}/file.json",
        f"io/test/test/{job_pk}/images/test/example.dat",
        f"io/test/test/{job_pk}/inputs.json",
        f"io/test/test/{job_pk}/prefix/1/images/test/example.dat",
        f"io/test/test/{job_pk}/prefix/2/file.json",
        f"io/test/test/{job_pk}/prefix/3/value.json",
        f"io/test/test/{job_pk}/value.json",
    }

    with io.BytesIO() as fileobj:
        executor._s3_client.download_fileobj(
            Fileobj=fileobj,
            Bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
            Key=f"invocations/test/test/{job_pk}/invocation.json",
        )
        fileobj.seek(0)
        invocation = json.loads(fileobj.read().decode("utf-8"))

    assert invocation == [
        {
            "inputs": [
                {
                    "bucket_key": f"/io/test/test/{job_pk}/images/test/example.dat",
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": "images/test/example.dat",
                },
                {
                    "bucket_key": f"/io/test/test/{job_pk}/file.json",
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": "file.json",
                },
                {
                    "bucket_key": f"/io/test/test/{job_pk}/value.json",
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": "value.json",
                },
                {
                    "bucket_key": f"/io/test/test/{job_pk}/prefix/1/images/test/example.dat",
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": "prefix/1/images/test/example.dat",
                },
                {
                    "bucket_key": f"/io/test/test/{job_pk}/prefix/2/file.json",
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": "prefix/2/file.json",
                },
                {
                    "bucket_key": f"/io/test/test/{job_pk}/prefix/3/value.json",
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": "prefix/3/value.json",
                },
                {
                    "bucket_key": f"/io/test/test/{job_pk}/inputs.json",
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": "inputs.json",
                },
            ],
            "output_bucket_name": "grand-challenge-components-outputs",
            "output_prefix": f"/io/test/test/{job_pk}",
            "pk": f"test-test-{job_pk}",
            "timeout": "PT1M40S",
        },
    ]


class _DummyStreamCM:
    """Async context manager to mimic httpx_client.stream(...)."""

    def __init__(self, resp):
        self.resp = resp

    async def __aenter__(self):
        return self.resp

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _make_resp(chunks):
    """
    Create a fake httpx response object:
    - raise_for_status is a sync mock
    - aiter_bytes returns an async generator that yields items in `chunks`
      (items can be bytes or Exception instances to raise).
    """
    resp = Mock()
    resp.raise_for_status = Mock()

    async def _aiter(chunk_size=None):
        for c in chunks:
            if isinstance(c, Exception):
                raise c
            yield c

    resp.aiter_bytes = lambda chunk_size=None: _aiter(chunk_size)
    return resp


@pytest.mark.asyncio
async def test_s3_stream_response_writes_object_to_s3_endpoint(settings):
    document = [
        b"h" * 5 * settings.MEGABYTE,
        b"",
        b"w" * 5 * settings.MEGABYTE,
        b"!" * 5 * settings.MEGABYTE,
    ]
    resp = _make_resp(document)
    httpx_client = Mock()
    httpx_client.stream = Mock(return_value=_DummyStreamCM(resp))

    semaphore = asyncio.Semaphore(ASYNC_CONCURRENCY)
    session = aioboto3.Session()

    key = f"test-{uuid4()}"
    bucket = settings.COMPONENTS_INPUT_BUCKET_NAME

    async with session.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        config=ASYNC_BOTO_CONFIG,
    ) as s3_client:
        await s3_stream_response(
            request_kwargs={"url": "http://example.local/resource"},
            bucket=bucket,
            key=key,
            httpx_client=httpx_client,
            s3_client=s3_client,
            semaphore=semaphore,
        )

        obj = await s3_client.get_object(Bucket=bucket, Key=key)
        body = await obj["Body"].read()
        assert body == b"".join(document)


@pytest.mark.asyncio
async def test_s3_stream_response_aborts_on_stream_error(settings):
    resp = _make_resp([b"part1", RuntimeError("stream-failure")])
    httpx_client = Mock()
    httpx_client.stream = Mock(return_value=_DummyStreamCM(resp))

    semaphore = asyncio.Semaphore(ASYNC_CONCURRENCY)
    session = aioboto3.Session()

    key = f"test-{uuid4()}"
    bucket = settings.COMPONENTS_INPUT_BUCKET_NAME

    async with session.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        config=ASYNC_BOTO_CONFIG,
    ) as s3_client:
        with pytest.raises(RuntimeError, match="stream-failure"):
            await s3_stream_response(
                request_kwargs={"url": "http://example.local/resource"},
                bucket=bucket,
                key=key,
                httpx_client=httpx_client,
                s3_client=s3_client,
                semaphore=semaphore,
            )

        with pytest.raises(botocore.exceptions.ClientError) as excinfo:
            await s3_client.head_object(Bucket=bucket, Key=key)

        status_code = excinfo.value.response["ResponseMetadata"][
            "HTTPStatusCode"
        ]
        assert status_code == 404


def normalize_partial(partial):
    keywords = dict(partial.keywords)

    if "content" in keywords:
        keywords["content"] = json.loads(keywords["content"].decode("utf-8"))

    return {"func": partial.func.__name__, **keywords}


@pytest.mark.django_db
def test_dicom_get_provisioning_tasks():
    job_pk = uuid4()

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        time_limit=100,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
    )

    panimage_interface = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.PANIMG_IMAGE,
        relative_path="images/test",
    )
    dicom_interface = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.DICOM_IMAGE_SET,
        relative_path="images/dicom",
    )

    panimage_civ = panimage_interface.create_instance(
        image=ImageFileFactory().image
    )
    dicom_civ = dicom_interface.create_instance(
        image=ImageFactory(dicom_image_set=DICOMImageSetFactory())
    )
    prefixed_panimage_civ = panimage_interface.create_instance(
        image=ImageFileFactory().image
    )
    prefixed_dicom_civ = dicom_interface.create_instance(
        image=ImageFactory(dicom_image_set=DICOMImageSetFactory())
    )

    tasks = executor._get_provisioning_tasks(
        input_civs=[
            panimage_civ,
            dicom_civ,
            prefixed_panimage_civ,
            prefixed_dicom_civ,
        ],
        input_prefixes={
            str(prefixed_panimage_civ.pk): "prefix/1",
            str(prefixed_dicom_civ.pk): "prefix/2",
        },
    )

    normalized_tasks = [normalize_partial(t) for t in tasks]

    assert len(normalized_tasks) == 14

    assert normalized_tasks[0]["func"] == "s3_copy"
    assert normalized_tasks[0]["source_key"] == panimage_civ.image_file
    assert (
        normalized_tasks[0]["target_key"]
        == f"/io/test/test/{job_pk}/images/test/example.dat"
    )

    for ii in range(5):
        task = normalized_tasks[ii + 1]
        image_set_id = dicom_civ.image.dicom_image_set.image_set_id
        image_frame = dicom_civ.image.dicom_image_set.image_frame_metadata[ii]

        study_instance_uid = image_frame["study_instance_uid"]
        series_instance_uid = image_frame["series_instance_uid"]
        sop_instance_uid = image_frame["sop_instance_uid"]
        stored_transfer_syntax_uid = image_frame["stored_transfer_syntax_uid"]

        assert task["func"] == "s3_sign_request_then_stream"
        assert (
            task["request"].url
            == f"https://dicom-medical-imaging.eu-central-1.amazonaws.com/datastore/None/studies/{study_instance_uid}/series/{series_instance_uid}/instances/{sop_instance_uid}?imageSetId={image_set_id}"
        )
        assert (
            task["request"].headers["Accept"]
            == f"application/dicom; transfer-syntax={stored_transfer_syntax_uid}"
        )
        assert isinstance(task["signer"], SigV4Auth)
        assert (
            task["key"]
            == f"/io/test/test/{job_pk}/images/dicom/{sop_instance_uid}.dcm"
        )

    assert normalized_tasks[6]["func"] == "s3_copy"
    assert (
        normalized_tasks[6]["source_key"] == prefixed_panimage_civ.image_file
    )
    assert (
        normalized_tasks[6]["target_key"]
        == f"/io/test/test/{job_pk}/prefix/1/images/test/example.dat"
    )

    for ii in range(5):
        task = normalized_tasks[ii + 7]
        image_set_id = prefixed_dicom_civ.image.dicom_image_set.image_set_id
        image_frame = (
            prefixed_dicom_civ.image.dicom_image_set.image_frame_metadata[ii]
        )

        study_instance_uid = image_frame["study_instance_uid"]
        series_instance_uid = image_frame["series_instance_uid"]
        sop_instance_uid = image_frame["sop_instance_uid"]
        stored_transfer_syntax_uid = image_frame["stored_transfer_syntax_uid"]

        assert task["func"] == "s3_sign_request_then_stream"
        assert (
            task["request"].url
            == f"https://dicom-medical-imaging.eu-central-1.amazonaws.com/datastore/None/studies/{study_instance_uid}/series/{series_instance_uid}/instances/{sop_instance_uid}?imageSetId={image_set_id}"
        )
        assert (
            task["request"].headers["Accept"]
            == f"application/dicom; transfer-syntax={stored_transfer_syntax_uid}"
        )
        assert isinstance(task["signer"], SigV4Auth)
        assert (
            task["key"]
            == f"/io/test/test/{job_pk}/prefix/2/images/dicom/{sop_instance_uid}.dcm"
        )

    assert normalized_tasks[13]["func"] == "s3_upload_content"
    assert (
        normalized_tasks[13]["key"]
        == f"/invocations/test/test/{job_pk}/invocation.json"
    )
    assert normalized_tasks[13]["content"] == [
        {
            "inputs": [
                {
                    "bucket_key": f"/io/test/test/{job_pk}/images/test/example.dat",
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": "images/test/example.dat",
                },
                {
                    "bucket_key": f'/io/test/test/{job_pk}/images/dicom/{dicom_civ.image.dicom_image_set.image_frame_metadata[0]["sop_instance_uid"]}.dcm',
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": f'images/dicom/{dicom_civ.image.dicom_image_set.image_frame_metadata[0]["sop_instance_uid"]}.dcm',
                },
                {
                    "bucket_key": f'/io/test/test/{job_pk}/images/dicom/{dicom_civ.image.dicom_image_set.image_frame_metadata[1]["sop_instance_uid"]}.dcm',
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": f'images/dicom/{dicom_civ.image.dicom_image_set.image_frame_metadata[1]["sop_instance_uid"]}.dcm',
                },
                {
                    "bucket_key": f'/io/test/test/{job_pk}/images/dicom/{dicom_civ.image.dicom_image_set.image_frame_metadata[2]["sop_instance_uid"]}.dcm',
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": f'images/dicom/{dicom_civ.image.dicom_image_set.image_frame_metadata[2]["sop_instance_uid"]}.dcm',
                },
                {
                    "bucket_key": f'/io/test/test/{job_pk}/images/dicom/{dicom_civ.image.dicom_image_set.image_frame_metadata[3]["sop_instance_uid"]}.dcm',
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": f'images/dicom/{dicom_civ.image.dicom_image_set.image_frame_metadata[3]["sop_instance_uid"]}.dcm',
                },
                {
                    "bucket_key": f'/io/test/test/{job_pk}/images/dicom/{dicom_civ.image.dicom_image_set.image_frame_metadata[4]["sop_instance_uid"]}.dcm',
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": f'images/dicom/{dicom_civ.image.dicom_image_set.image_frame_metadata[4]["sop_instance_uid"]}.dcm',
                },
                {
                    "bucket_key": f"/io/test/test/{job_pk}/prefix/1/images/test/example.dat",
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": "prefix/1/images/test/example.dat",
                },
                {
                    "bucket_key": f'/io/test/test/{job_pk}/prefix/2/images/dicom/{prefixed_dicom_civ.image.dicom_image_set.image_frame_metadata[0]["sop_instance_uid"]}.dcm',
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": f'prefix/2/images/dicom/{prefixed_dicom_civ.image.dicom_image_set.image_frame_metadata[0]["sop_instance_uid"]}.dcm',
                },
                {
                    "bucket_key": f'/io/test/test/{job_pk}/prefix/2/images/dicom/{prefixed_dicom_civ.image.dicom_image_set.image_frame_metadata[1]["sop_instance_uid"]}.dcm',
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": f'prefix/2/images/dicom/{prefixed_dicom_civ.image.dicom_image_set.image_frame_metadata[1]["sop_instance_uid"]}.dcm',
                },
                {
                    "bucket_key": f'/io/test/test/{job_pk}/prefix/2/images/dicom/{prefixed_dicom_civ.image.dicom_image_set.image_frame_metadata[2]["sop_instance_uid"]}.dcm',
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": f'prefix/2/images/dicom/{prefixed_dicom_civ.image.dicom_image_set.image_frame_metadata[2]["sop_instance_uid"]}.dcm',
                },
                {
                    "bucket_key": f'/io/test/test/{job_pk}/prefix/2/images/dicom/{prefixed_dicom_civ.image.dicom_image_set.image_frame_metadata[3]["sop_instance_uid"]}.dcm',
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": f'prefix/2/images/dicom/{prefixed_dicom_civ.image.dicom_image_set.image_frame_metadata[3]["sop_instance_uid"]}.dcm',
                },
                {
                    "bucket_key": f'/io/test/test/{job_pk}/prefix/2/images/dicom/{prefixed_dicom_civ.image.dicom_image_set.image_frame_metadata[4]["sop_instance_uid"]}.dcm',
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": f'prefix/2/images/dicom/{prefixed_dicom_civ.image.dicom_image_set.image_frame_metadata[4]["sop_instance_uid"]}.dcm',
                },
                {
                    "bucket_key": f"/io/test/test/{job_pk}/inputs.json",
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": "inputs.json",
                },
            ],
            "output_bucket_name": "grand-challenge-components-outputs",
            "output_prefix": f"/io/test/test/{job_pk}",
            "pk": f"test-test-{job_pk}",
            "timeout": "PT1M40S",
        },
    ]


@pytest.mark.django_db
def test_dodgy_sop_instance_uid():
    job_pk = uuid4()

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        time_limit=100,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
    )

    dicom_interface = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.DICOM_IMAGE_SET,
        relative_path="images/dicom",
    )

    dicom_civ = dicom_interface.create_instance(
        image=ImageFactory(
            dicom_image_set=DICOMImageSetFactory(
                image_frame_metadata=[
                    {
                        "image_frame_id": "123",
                        "frame_size_in_bytes": 1337,
                        "study_instance_uid": "123",
                        "series_instance_uid": "123",
                        "sop_instance_uid": "../fds",
                        "stored_transfer_syntax_uid": "1.2.840.10008.1.2.4.202",
                    }
                ]
            )
        )
    )

    with pytest.raises(SuspiciousFileOperation) as exec_info:
        executor._get_provisioning_tasks(
            input_civs=[dicom_civ], input_prefixes={}
        )

    assert (
        "images/fds.dcm) is located outside of the base path component"
        in str(exec_info.value)
    )


def test_signing_key_env_set():
    job_pk = uuid4()

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        time_limit=100,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"1337",
    )

    assert (
        executor.invocation_environment[
            "GRAND_CHALLENGE_COMPONENT_SIGNING_KEY_HEX"
        ]
        == "31333337"
    )


def test_invocation_results_signature_unverified(settings):
    job_pk = uuid4()

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        time_limit=100,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"correct-key",
    )

    inference_result = InferenceResult(
        pk=f"test-test-{job_pk}",
        return_code=0,
        exec_duration=timedelta(seconds=1337),
        invoke_duration=None,
        outputs=[],
        sagemaker_shim_version="0.5.0",
    )
    inference_result_content = inference_result.model_dump_json().encode(
        "utf-8"
    )
    signature = hmac.new(
        key=b"wrong-key",
        msg=inference_result_content,
        digestmod=hashlib.sha256,
    ).hexdigest()

    executor._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(inference_result_content),
        Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
        Key=executor._result_key,
        ExtraArgs={
            "Metadata": {"signature_hmac_sha256": signature},
        },
    )

    with pytest.raises(ComponentException) as error:
        executor._get_inference_result()

    assert (
        str(error.value)
        == "The invocation response object has been tampered with"
    )


def test_invocation_results_signature_verified(settings):
    job_pk = uuid4()

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        time_limit=100,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"correct-key",
    )

    inference_result = InferenceResult(
        pk=f"test-test-{job_pk}",
        return_code=0,
        exec_duration=timedelta(seconds=1337),
        invoke_duration=None,
        outputs=[],
        sagemaker_shim_version="0.5.0",
    )
    inference_result_content = inference_result.model_dump_json().encode(
        "utf-8"
    )
    signature = hmac.new(
        key=b"correct-key",
        msg=inference_result_content,
        digestmod=hashlib.sha256,
    ).hexdigest()

    executor._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(inference_result_content),
        Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
        Key=executor._result_key,
        ExtraArgs={
            "Metadata": {"signature_hmac_sha256": signature},
        },
    )

    assert executor._get_inference_result() == inference_result
