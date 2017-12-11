import random
import pytest
import json

from datetime import timedelta

from django.http.response import JsonResponse
from django.test.client import RequestFactory

from jqfileupload.widgets.uploader import AjaxUploadWidget


@pytest.mark.django_db
def test_one_big_upload(rf: RequestFactory):
    widget = AjaxUploadWidget(ajax_target_path="/ajax")
    widget.timeout = timedelta(seconds=1)

    boundary = "RandomBoundaryFTWBlablablablalba8923475278934578"

    filename = "test.tgz"
    content = random.getrandbits(8 * 1000000).to_bytes(1000000, 'little')

    data = f"""
--{boundary}\r
Content-Disposition: form-data; name="files[]"; filename="test.tgz"\r
Content-Type: application/octet-stream\r
\r
""".lstrip().encode() + content + f"""\r
--{boundary}--""".encode()

    post_request = rf.post(
        "/ajax",
        data=data,
        content_type=f"multipart/form-data; boundary={boundary}",
        **{"X-CSRFToken": "tests_csrf_token"})
    post_request.META["CSRF_COOKIE"] = "tests_csrf_token"

    response = widget.handle_ajax(post_request)

    assert isinstance(response, JsonResponse)

    parsed_json = json.loads(response.content)
    assert len(parsed_json) == 1

    assert parsed_json[0]["filename"] == filename
    assert "uuid" in parsed_json[0]
    assert "extra_attrs" in parsed_json[0]


def test_rfc7233_implementation(rf: RequestFactory):
    pass
