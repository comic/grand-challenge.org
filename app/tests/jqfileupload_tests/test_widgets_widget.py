import os
import uuid
import random
import json
import time

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError

from django.http.response import JsonResponse, HttpResponseForbidden, \
    HttpResponseBadRequest
from django.test.client import RequestFactory

from jqfileupload.models import StagedFile
from jqfileupload.widgets.uploader import AjaxUploadWidget, StagedAjaxFile, \
    UploadedAjaxFileList


def load_test_data():
    with open(
            os.path.join(os.path.dirname(__file__), "testdata", "rnddata"),
            'rb') as f:
        return f.read()

def generate_new_upload_id(sender, content):
    return f"{id(sender)}_{hash(content)}_{time.time()}_{random.random()}"

def create_upload_file_request(
        rf: RequestFactory,
        filename: str="test.bin",
        boundary: str="RandomBoundaryFTWBlablablablalba8923475278934578",
        content: bytes=None,
        csrf_token: str="tests_csrf_token",
        extra_fields: dict={},
        extra_headers: dict={}):
    if content is None:
        content = load_test_data()

    ##### Basic request #####
    data = f"""
--{boundary}\r
Content-Disposition: form-data; name="files[]"; filename="{filename}"\r
Content-Type: application/octet-stream\r
\r
""".lstrip().encode() + content + f"""\r
--{boundary}--""".encode()

    ##### Add additional fields #####
    for key, value in extra_fields.items():
        extra_field_data = f"""
--{boundary}\r
Content-Disposition: form-data; name="{key}"\r
\r
{value}\r
""".lstrip().encode()
        data = extra_field_data + data

    headers = {
        "X-CSRFToken": csrf_token
    }
    for key, value in extra_headers.items():
        headers[key] = value

    post_request = rf.post(
        "/ajax",
        data=data,
        content_type=f"multipart/form-data; boundary={boundary}",
        **headers)
    post_request.META["CSRF_COOKIE"] = csrf_token

    return post_request


def create_partial_upload_file_request(
        rf: RequestFactory,
        upload_identifer: str,
        content: bytes,
        start_byte: int,
        end_byte: int,
        filename: str = "test.bin"):
    content_range = f"bytes {start_byte}-{end_byte-1}/{len(content)}"

    post_request = create_upload_file_request(
        rf,
        filename=filename,
        content=content[start_byte:end_byte],
        extra_headers={
            "Content-Range": content_range
        },
        extra_fields={
            "X-Upload-ID": upload_identifer
        })

    post_request.META["HTTP_CONTENT_RANGE"] = content_range

    return post_request


def test_invalid_initialization():
    with pytest.raises(ValueError):
        AjaxUploadWidget()

@pytest.mark.django_db
def test_single_chunk(rf: RequestFactory):
    widget = AjaxUploadWidget(ajax_target_path="/ajax")
    widget.timeout = timedelta(seconds=1)

    filename = 'test.bin'
    post_request = create_upload_file_request(rf, filename=filename)
    response = widget.handle_ajax(post_request)
    assert isinstance(response, JsonResponse)

    parsed_json = json.loads(response.content)
    assert len(parsed_json) == 1

    assert parsed_json[0]["filename"] == filename
    assert "uuid" in parsed_json[0]
    assert "extra_attrs" in parsed_json[0]

    staged_file = StagedAjaxFile(uuid.UUID(parsed_json[0]["uuid"]))
    with staged_file.open() as f:
        staged_content = f.read()

    assert staged_content == load_test_data()

@pytest.mark.django_db
def test_rfc7233_implementation(rf: RequestFactory):
    content = load_test_data()
    upload_id = generate_new_upload_id(test_rfc7233_implementation, content)

    part_1 = create_partial_upload_file_request(
        rf, upload_id, content, 0, 10)
    part_2 = create_partial_upload_file_request(
        rf, upload_id, content, 10, len(content) // 2)
    part_3 = create_partial_upload_file_request(
        rf, upload_id, content, len(content) // 2, len(content))

    widget = AjaxUploadWidget(ajax_target_path="/ajax")
    widget.timeout = timedelta(seconds=1)

    response = widget.handle_ajax(part_1)
    assert isinstance(response, JsonResponse)
    response = widget.handle_ajax(part_2)
    assert isinstance(response, JsonResponse)
    response = widget.handle_ajax(part_3)
    assert isinstance(response, JsonResponse)

    parsed_json = json.loads(response.content)
    staged_file = StagedAjaxFile(uuid.UUID(parsed_json[0]["uuid"]))

    with staged_file.open() as f:
        staged_content = f.read()

    assert staged_content == content

@pytest.mark.django_db
def test_wrong_upload_headers(rf: RequestFactory):
    widget = AjaxUploadWidget(ajax_target_path="/ajax")
    widget.timeout = timedelta(seconds=1)

    post_request = create_upload_file_request(rf)
    post_request.META["CSRF_COOKIE"] = None
    assert isinstance(widget.handle_ajax(post_request), HttpResponseForbidden)

    post_request = create_upload_file_request(rf)
    post_request.method = "PUT"
    assert isinstance(widget.handle_ajax(post_request), HttpResponseBadRequest)

@pytest.mark.django_db
def test_wrong_upload_headers_rfc7233(rf: RequestFactory):
    widget = AjaxUploadWidget(ajax_target_path="/ajax")
    widget.timeout = timedelta(seconds=1)

    content = load_test_data()
    upload_id = generate_new_upload_id(test_wrong_upload_headers_rfc7233, content)
    post_request = create_partial_upload_file_request(
        rf, upload_id, content, 0, 10)
    assert isinstance(widget.handle_ajax(post_request), JsonResponse)

    post_request = create_partial_upload_file_request(
        rf, upload_id, content, 0, 10)
    post_request.META["X-Upload-ID"] = None
    post_request.POST["X-Upload-ID"] = None
    assert isinstance(widget.handle_ajax(post_request), HttpResponseBadRequest)

    post_request = create_partial_upload_file_request(
        rf, upload_id, content, 0, 10)
    post_request.META["HTTP_CONTENT_RANGE"] = "corrupted data: 54343-3223/21323"
    assert isinstance(widget.handle_ajax(post_request), HttpResponseBadRequest)

    post_request = create_partial_upload_file_request(
        rf, upload_id, content, 0, 10)
    post_request.META["HTTP_CONTENT_RANGE"] = "bytes 54343-3223/21323"
    assert isinstance(widget.handle_ajax(post_request), HttpResponseBadRequest)

    post_request = create_partial_upload_file_request(
        rf, upload_id, content, 0, 10)
    post_request.META["HTTP_CONTENT_RANGE"] = "bytes 54343-3223/*"
    assert isinstance(widget.handle_ajax(post_request), HttpResponseBadRequest)

    post_request = create_partial_upload_file_request(
        rf, upload_id, content, 0, 10)
    post_request.META["HTTP_CONTENT_RANGE"] = "bytes 1000-3000/2000"
    assert isinstance(widget.handle_ajax(post_request), HttpResponseBadRequest)

    post_request = create_partial_upload_file_request(
        rf, upload_id, content, 0, 10)
    post_request.META["HTTP_CONTENT_RANGE"] = "bytes 1000-2000/*"
    assert isinstance(widget.handle_ajax(post_request), HttpResponseBadRequest)

    post_request = create_partial_upload_file_request(
        rf, upload_id, content, 0, 10)
    post_request.META["X-Upload-ID"] = "a" * 1000
    post_request.POST["X-Upload-ID"] = "a" * 1000
    assert isinstance(widget.handle_ajax(post_request), HttpResponseBadRequest)

@pytest.mark.django_db
def test_inconsistent_chunks_rfc7233(rf: RequestFactory):
    widget = AjaxUploadWidget(ajax_target_path="/ajax")
    widget.timeout = timedelta(seconds=1)

    content = load_test_data()

    # Overlapping chunks
    upload_id = generate_new_upload_id(test_inconsistent_chunks_rfc7233, content)
    part_1 = create_partial_upload_file_request(
        rf, upload_id, content, 0, 10)
    part_2 = create_partial_upload_file_request(
        rf, upload_id, content, 5, 15)

    widget.handle_ajax(part_1)
    assert isinstance(widget.handle_ajax(part_2), HttpResponseBadRequest)

    # Inconsistent filenames
    upload_id += "x"
    part_1 = create_partial_upload_file_request(
        rf, upload_id, content, 0, 10, filename="a")
    part_2 = create_partial_upload_file_request(
        rf, upload_id, content, 10, 20, filename="b")

    widget.handle_ajax(part_1)
    assert isinstance(widget.handle_ajax(part_2), HttpResponseBadRequest)

    # Inconsistent total size
    upload_id += "x"
    part_1 = create_partial_upload_file_request(
        rf, upload_id, content[:20], 0, 10)
    part_2 = create_partial_upload_file_request(
        rf, upload_id, content[:20], 10, 20)
    part_1.META["HTTP_CONTENT_RANGE"] = f"bytes 0-9/20"
    part_2.META["HTTP_CONTENT_RANGE"] = f"bytes 10-19/30"

    widget.handle_ajax(part_1)
    assert isinstance(widget.handle_ajax(part_2), HttpResponseBadRequest)


def test_render():
    widget = AjaxUploadWidget(ajax_target_path="/ajax", multifile=True)
    render_result = widget.render("some_name", None)
    assert isinstance(render_result, str)
    render_result = widget.render("some_name", (uuid.uuid4(), uuid.uuid4()))
    assert isinstance(render_result, str)

    widget = AjaxUploadWidget(ajax_target_path="/ajax", multifile=False)
    render_result = widget.render("some_name", None)
    assert isinstance(render_result, str)
    render_result = widget.render("some_name", (uuid.uuid4(), uuid.uuid4()))
    assert isinstance(render_result, str)


def test_form_field_to_python():
    form_field = UploadedAjaxFileList()

    uuid_string = "4dec34db-930f-48be-bb65-d7f8319ff654," + \
        "5d901b2c-7cd1-416e-9952-d30b6a0edcba," + \
        "4a3c5731-0050-4489-8364-282278f7190f"
    staged_files = form_field.to_python(uuid_string)

    assert ",".join(str(sf.uuid) for sf in staged_files) == uuid_string

    with pytest.raises(ValidationError):
        form_field.to_python("asdfasdfsdafasdf")

    other_string = uuid_string[10:]
    with pytest.raises(ValidationError):
        form_field.to_python(other_string)


def test_form_field_prepare_value_not_implemented():
    form_field = UploadedAjaxFileList()
    assert form_field.prepare_value("") is None
