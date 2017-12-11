import os
import uuid

import pytest
import json

from datetime import timedelta

from django.http.response import JsonResponse
from django.test.client import RequestFactory

from jqfileupload.models import StagedFile
from jqfileupload.widgets.uploader import AjaxUploadWidget, StagedAjaxFile


def load_test_data():
    with open(
            os.path.join(os.path.dirname(__file__), "testdata", "rnddata"),
            'rb') as f:
        return f.read()


def create_upload_file_request(
        rf: RequestFactory,
        filename: str="test.bin",
        boundary: str="RandomBoundaryFTWBlablablablalba8923475278934578",
        content: bytes=None,
        csrf_token: str="tests_csrf_token",
        extra_fields: dict={}):
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

    post_request = rf.post(
        "/ajax",
        data=data,
        content_type=f"multipart/form-data; boundary={boundary}",
        **{"X-CSRFToken": csrf_token})
    post_request.META["CSRF_COOKIE"] = csrf_token

    return post_request


@pytest.mark.django_db
def test_one_big_upload(rf: RequestFactory):
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
        assert f.read() == load_test_data()


def test_rfc7233_implementation(rf: RequestFactory):
    pass
