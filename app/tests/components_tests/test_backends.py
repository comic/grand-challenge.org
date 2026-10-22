import asyncio
import hashlib
import hmac
import io
import json
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
from django.utils.timezone import now

from grandchallenge.components.backends.base import (
    ASYNC_BOTO_CONFIG,
    ASYNC_CONCURRENCY,
    Executor,
    InferenceResult,
    InferenceTaskDefinition,
    RuntimeSetupResult,
    s3_stream_response,
)
from grandchallenge.components.backends.exceptions import ComponentException
from grandchallenge.components.backends.utils import (
    NO_ERRORS_IN_LOG_MESSAGE,
    _filter_members,
    user_error,
)
from grandchallenge.components.models import (
    APIMethodChoices,
    InterfaceKindChoices,
)
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.components.tasks import handle_event
from grandchallenge.evaluation.models import BatchJob
from tests.cases_tests.factories import DICOMImageSetFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.components_tests.resources.backends import IOCopyExecutor
from tests.evaluation_tests.factories import BatchJobFactory
from tests.factories import ImageFactory, ImageFileFactory


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
    assert user_error(obj=f"{timestamp}\n") == NO_ERRORS_IN_LOG_MESSAGE
    assert (
        user_error(obj=f"{timestamp}\n{timestamp}\n")
        == NO_ERRORS_IN_LOG_MESSAGE
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

    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(
        2, interface__kind=InterfaceKindChoices.ANY
    )

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
        api_method=APIMethodChoices.EXEC,
        task_definitions=[
            InferenceTaskDefinition(
                input_civs=[civ1, civ2], time_limit=timedelta(seconds=100)
            )
        ],
    )

    executor.provision()

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
            "socket": {
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
            "socket": {
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

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
        api_method=APIMethodChoices.EXEC,
        task_definitions=[
            InferenceTaskDefinition(
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
                time_limit=timedelta(seconds=100),
            )
        ],
    )

    executor.provision()

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

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
        api_method=APIMethodChoices.EXEC,
        task_definitions=[
            InferenceTaskDefinition(
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
                time_limit=timedelta(seconds=100),
            )
        ],
    )
    tasks = executor.provisioning_tasks

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

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
        api_method=APIMethodChoices.EXEC,
        task_definitions=[
            InferenceTaskDefinition(
                input_civs=[dicom_civ],
                time_limit=timedelta(seconds=100),
            )
        ],
    )

    with pytest.raises(SuspiciousFileOperation) as exec_info:
        executor.provisioning_tasks

    assert (
        "images/fds.dcm) is located outside of the base path component"
        in str(exec_info.value)
    )


@pytest.mark.django_db
def test_multiple_provisioning_tasks_build_one_inference_task_each():
    job_pk = uuid4()

    value_interface = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY,
        relative_path="value.json",
        store_in_database=True,
    )
    first_civ = value_interface.create_instance(value="first")
    second_civ = value_interface.create_instance(value="second")

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
        api_method=APIMethodChoices.EXEC,
        task_definitions=[
            InferenceTaskDefinition(
                task_pk="1234",
                input_civs=[first_civ],
                time_limit=timedelta(minutes=10),
            ),
            InferenceTaskDefinition(
                task_pk="5678",
                input_civs=[second_civ],
                time_limit=timedelta(minutes=5),
            ),
        ],
    )

    first_prefix = executor._get_output_prefix_for_task(task_pk="1234")
    second_prefix = executor._get_output_prefix_for_task(task_pk="5678")

    tasks = executor.provisioning_tasks

    normalized_tasks = [normalize_partial(t) for t in tasks]

    invocation_task = normalized_tasks[-1]
    assert invocation_task["func"] == "s3_upload_content"
    assert (
        invocation_task["key"]
        == f"/invocations/test/test/{job_pk}/invocation.json"
    )

    inference_tasks = invocation_task["content"]
    assert len(inference_tasks) == 2

    assert inference_tasks[0]["pk"] == f"test-test-{job_pk}-1234"
    assert inference_tasks[0]["output_prefix"] == first_prefix
    assert {i["relative_path"] for i in inference_tasks[0]["inputs"]} == {
        "value.json",
        "inputs.json",
    }
    assert inference_tasks[0]["timeout"] == "PT10M"

    assert inference_tasks[1]["pk"] == f"test-test-{job_pk}-5678"
    assert inference_tasks[1]["output_prefix"] == second_prefix
    assert {i["relative_path"] for i in inference_tasks[1]["inputs"]} == {
        "value.json",
        "inputs.json",
    }
    assert inference_tasks[1]["timeout"] == "PT5M"


@pytest.mark.django_db
def test_relative_paths_use_task_output_prefix():
    job_pk = uuid4()

    value_interface = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY,
        relative_path="value.json",
        store_in_database=True,
    )
    civ = value_interface.create_instance(value="foo")

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
        api_method=APIMethodChoices.EXEC,
        task_definitions=[
            InferenceTaskDefinition(
                task_pk="1234",
                input_civs=[civ],
                time_limit=timedelta(minutes=10),
            )
        ],
    )

    output_prefix = executor._get_output_prefix_for_task(task_pk="1234")

    tasks = executor.provisioning_tasks

    normalized_tasks = [normalize_partial(t) for t in tasks]

    value_task = normalized_tasks[0]
    assert value_task["func"] == "s3_upload_content"
    assert value_task["key"] == f"{output_prefix}/value.json"

    inference_task = normalized_tasks[-1]["content"][0]
    value_input = next(
        i
        for i in inference_task["inputs"]
        if i["relative_path"] == "value.json"
    )
    assert value_input["bucket_key"] == f"{output_prefix}/value.json"


@pytest.mark.django_db
def test_provision_batch_job(settings):
    str_interface = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.STRING,
        relative_path="string.json",
        store_in_database=True,
    )

    batch_job = BatchJobFactory(
        input_civ_sets=[
            {str_interface.create_instance(value="first")},
            {str_interface.create_instance(value="second")},
        ],
        time_limit=10,
    )
    first_task, second_task = batch_job.tasks.all()

    executor = IOCopyExecutor(
        **{
            **batch_job.executor_kwargs,
            "task_definitions": [
                InferenceTaskDefinition(
                    input_civs=task.inputs.all(),
                    task_pk=str(task.pk),
                    time_limit=timedelta(minutes=10),
                )
                for task in batch_job.tasks.prefetch_related(
                    "inputs__interface", "inputs__image__files"
                ).all()
            ],
        }
    )

    executor.provision()

    first_prefix = executor._get_output_prefix_for_task(
        task_pk=str(first_task.pk)
    )
    second_prefix = executor._get_output_prefix_for_task(
        task_pk=str(second_task.pk)
    )

    with io.BytesIO() as fileobj:
        executor._s3_client.download_fileobj(
            Fileobj=fileobj,
            Bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
            Key=executor._invocation_key,
        )
        fileobj.seek(0)
        invocation = json.loads(fileobj.read().decode("utf-8"))

    assert len(invocation) == 2

    inference_tasks_by_prefix = {
        inference_task["output_prefix"]: inference_task
        for inference_task in invocation
    }
    assert set(inference_tasks_by_prefix) == {first_prefix, second_prefix}

    for prefix in (first_prefix, second_prefix):
        inference_task = inference_tasks_by_prefix[prefix]
        assert {i["relative_path"] for i in inference_task["inputs"]} == {
            "string.json",
            "inputs.json",
        }
        assert (
            next(
                i
                for i in inference_task["inputs"]
                if i["relative_path"] == "string.json"
            )["bucket_key"]
            == f"{prefix}/string.json"
        )
        assert inference_task["timeout"] == "PT10M"


@pytest.mark.django_db
def test_test_executor_writes_result_per_task():
    str_interface = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.STRING,
        relative_path="string.json",
        store_in_database=True,
    )

    batch_job = BatchJobFactory(
        input_civ_sets=[
            {str_interface.create_instance(value="first")},
            {str_interface.create_instance(value="second")},
        ],
        time_limit=10,
    )

    task_definitions = [
        InferenceTaskDefinition(
            input_civs=task.inputs.all(),
            task_pk=str(task.pk),
            time_limit=timedelta(minutes=10),
        )
        for task in batch_job.tasks.prefetch_related(
            "inputs__interface", "inputs__image__files"
        ).all()
    ]

    executor = IOCopyExecutor(
        **{
            **batch_job.executor_kwargs,
            "task_definitions": task_definitions,
        }
    )

    executor.provision()
    executor.execute()

    inference_results = executor.inference_results

    assert len(inference_results) == 2
    assert {result.pk for result in inference_results} == {
        executor._get_inference_task_pk(task_pk=task_definition.task_pk)
        for task_definition in task_definitions
    }
    assert all(result.return_code == 0 for result in inference_results)


@pytest.mark.django_db
def test_batchjob_task_failure_fails_entire_job_with_task_error_message(
    settings,
):
    str_interface = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.STRING,
        relative_path="string.json",
        store_in_database=True,
    )
    batch_job = BatchJobFactory(
        status=BatchJob.EXECUTING,
        signing_key=b"correct-key",
        input_civ_sets=[
            {str_interface.create_instance(value="first")},
            {str_interface.create_instance(value="second")},
        ],
        time_limit=10,
    )

    backend = "tests.components_tests.resources.backends.IOCopyExecutor"
    executor = batch_job.get_executor(backend=backend)

    task_definitions = executor._task_definitions

    def upload_signed(*, obj, key):
        content = obj.model_dump_json().encode("utf-8")
        signature = hmac.new(
            key=b"correct-key",
            msg=content,
            digestmod=hashlib.sha256,
        ).hexdigest()
        executor._s3_client.upload_fileobj(
            Fileobj=io.BytesIO(content),
            Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
            Key=key,
            ExtraArgs={"Metadata": {"signature_hmac_sha256": signature}},
        )

    # The job-level runtime setup succeeded.
    upload_signed(
        obj=RuntimeSetupResult(
            return_code=0,
            user_safe_error_message="",
            sagemaker_shim_version="0.8.0",
        ),
        key=executor.runtime_setup_result_key,
    )

    # Only the first task wrote a result, and it failed. The second task's
    # result is absent.
    first_task_pk = task_definitions[0].task_pk
    upload_signed(
        obj=InferenceResult(
            pk=executor._get_inference_task_pk(task_pk=first_task_pk),
            return_code=1,
            user_safe_error_message="the first task failed",
            user_process_last_stderr_lines=[],
            exec_duration=timedelta(seconds=1),
            invoke_duration=timedelta(seconds=1),
            outputs=[],
            sagemaker_shim_version="0.8.0",
        ),
        key=executor._get_inference_result_key(task_pk=first_task_pk),
    )

    handle_event(
        event={
            "_job_id": batch_job.executor_kwargs["job_id"],
            "__start_time": now().isoformat(),
        },
        backend=backend,
    )

    batch_job.refresh_from_db()

    assert batch_job.status == BatchJob.FAILURE
    assert batch_job.error_message == "the first task failed"


def test_signing_key_env_set():
    job_pk = uuid4()

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"1337",
        api_method=APIMethodChoices.EXEC,
    )

    assert (
        executor.invocation_environment[
            "GRAND_CHALLENGE_COMPONENT_SIGNING_KEY_HEX"
        ]
        == "31333337"
    )


def test_api_method_env_set():
    job_pk = uuid4()

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"1337",
        api_method=APIMethodChoices.INVOKE,
    )

    assert (
        executor.invocation_environment["GRAND_CHALLENGE_COMPONENT_API_METHOD"]
        == "invoke"
    )


def test_runtime_setup_result_signature_unverified(settings):
    job_pk = uuid4()

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"correct-key",
        api_method=APIMethodChoices.EXEC,
    )

    runtime_setup_result = RuntimeSetupResult(
        return_code=0,
        user_safe_error_message="",
        sagemaker_shim_version="0.8.0",
    )
    runtime_setup_result_content = (
        runtime_setup_result.model_dump_json().encode("utf-8")
    )
    signature = hmac.new(
        key=b"wrong-key",
        msg=runtime_setup_result_content,
        digestmod=hashlib.sha256,
    ).hexdigest()
    executor._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(runtime_setup_result_content),
        Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
        Key=executor.runtime_setup_result_key,
        ExtraArgs={
            "Metadata": {"signature_hmac_sha256": signature},
        },
    )

    with pytest.raises(ComponentException) as error:
        executor._get_runtime_setup_result()

    assert str(error.value) == "A required output file has been tampered with"


def test_runtime_setup_result_signature_verified(settings):
    job_pk = uuid4()

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"correct-key",
        api_method=APIMethodChoices.EXEC,
    )

    runtime_setup_result = RuntimeSetupResult(
        return_code=0,
        user_safe_error_message="",
        sagemaker_shim_version="0.8.0",
    )
    runtime_setup_result_content = (
        runtime_setup_result.model_dump_json().encode("utf-8")
    )
    signature = hmac.new(
        key=b"correct-key",
        msg=runtime_setup_result_content,
        digestmod=hashlib.sha256,
    ).hexdigest()
    executor._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(runtime_setup_result_content),
        Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
        Key=executor.runtime_setup_result_key,
        ExtraArgs={
            "Metadata": {"signature_hmac_sha256": signature},
        },
    )

    assert executor._get_runtime_setup_result() == runtime_setup_result


def test_invocation_results_signature_unverified(settings):
    job_pk = uuid4()

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"correct-key",
        api_method=APIMethodChoices.EXEC,
    )

    inference_result = InferenceResult(
        pk=f"test-test-{job_pk}",
        return_code=0,
        user_safe_error_message="",
        user_process_last_stderr_lines=[],
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
        Key=executor._get_inference_result_key(),
        ExtraArgs={
            "Metadata": {"signature_hmac_sha256": signature},
        },
    )

    with pytest.raises(ComponentException) as error:
        executor._get_inference_result()

    assert str(error.value) == "A required output file has been tampered with"


def test_invocation_results_signature_verified(settings):
    job_pk = uuid4()

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"correct-key",
        api_method=APIMethodChoices.EXEC,
    )

    inference_result = InferenceResult(
        pk=f"test-test-{job_pk}",
        return_code=0,
        user_safe_error_message="",
        user_process_last_stderr_lines=[],
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
        Key=executor._get_inference_result_key(),
        ExtraArgs={
            "Metadata": {"signature_hmac_sha256": signature},
        },
    )

    assert executor._get_inference_result() == inference_result


@pytest.mark.parametrize(
    (
        "user_safe_error_message",
        "user_process_last_stderr_lines",
        "expected_error_message",
    ),
    (
        ("user safe error", [], "user safe error"),
        ("user safe error", [""], "user safe error"),
        ("user safe error", ["foo"], "user safe error"),
        ("user safe error", ["foo", "bar"], "user safe error"),
        (
            "",
            [],
            NO_ERRORS_IN_LOG_MESSAGE,
        ),
        (
            "",
            [""],
            NO_ERRORS_IN_LOG_MESSAGE,
        ),
        ("", ["user process error"], "user process error"),
        ("", ["pre error", "user process error"], "user process error"),
        (
            "",
            ["pre error", "\nuser process error \n\r\n", " ", "\n\n \n \r\n "],
            "user process error",
        ),
    ),
)
def test_get_error_message_from_inference_result(
    user_safe_error_message,
    user_process_last_stderr_lines,
    expected_error_message,
):
    inference_result = InferenceResult(
        pk="algorithms-job-1",
        return_code=1,
        user_safe_error_message=user_safe_error_message,
        user_process_last_stderr_lines=user_process_last_stderr_lines,
        exec_duration=timedelta(seconds=1),
        invoke_duration=timedelta(seconds=1),
        outputs=[],
        sagemaker_shim_version="0.8.1",
    )

    error_message = Executor._get_error_message(
        inference_result=inference_result
    )

    assert error_message == expected_error_message


@pytest.mark.django_db
def test_create_value_for_output_default_prefix(settings):
    job_pk = uuid4()

    interface = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.INTEGER,
        relative_path="output.json",
        store_in_database=True,
    )

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
        api_method=APIMethodChoices.EXEC,
        task_definitions=[
            InferenceTaskDefinition(
                input_civs=[], time_limit=timedelta(seconds=100)
            )
        ],
    )

    executor._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(b"42"),
        Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
        Key=f"io/test/test/{job_pk}/output.json",
    )

    civ = executor.create_value_for_output(interface=interface)

    assert civ.value == 42


@pytest.mark.django_db
def test_create_value_for_output_with_task_output_prefix(settings):
    job_pk = uuid4()
    task_pk = uuid4()

    interface = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.INTEGER,
        relative_path="output.json",
        store_in_database=True,
    )

    executor = IOCopyExecutor(
        job_id=f"test-test-{job_pk}",
        exec_image_repo_tag="test",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
        api_method=APIMethodChoices.EXEC,
        task_definitions=[
            InferenceTaskDefinition(
                input_civs=[],
                time_limit=timedelta(seconds=100),
                task_pk=str(task_pk),
            )
        ],
    )

    executor._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(b"1337"),
        Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
        Key=f"io/test/test/{job_pk}/{task_pk}/output.json",
    )

    civ = executor.create_value_for_output(
        interface=interface, task_pk=str(task_pk)
    )

    assert civ.value == 1337
