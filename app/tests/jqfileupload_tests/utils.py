import os
import time
import random

from django.test import RequestFactory


def load_test_data():
    with open(
            os.path.join(
                os.path.dirname(__file__),
                "testdata",
                "rnddata"),
            'rb') as f:
        return f.read()


def generate_new_upload_id(sender, content):
    return f"{id(sender)}_{hash(content)}_{time.time()}_{random.random()}"


def create_upload_file_request(
    rf: RequestFactory,
    filename: str = "test.bin",
    boundary: str = "RandomBoundaryFTWBlablablablalba8923475278934578",
    content: bytes = None,
    csrf_token: str = "tests_csrf_token",
    extra_fields: dict ={},
    extra_headers: dict ={},
):
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
    headers = {"X-CSRFToken": csrf_token}
    headers.update(extra_headers)
    headers["CSRF_COOKIE"] = csrf_token
    return rf.post(
        "/ajax",
        data=data,
        content_type=f"multipart/form-data; boundary={boundary}",
        **headers,
    )


def create_partial_upload_file_request(
    rf: RequestFactory,
    upload_identifer: str,
    content: bytes,
    start_byte: int,
    end_byte: int,
    filename: str = "test.bin",
):
    content_range = f"bytes {start_byte}-{end_byte-1}/{len(content)}"
    return create_upload_file_request(
        rf,
        filename=filename,
        content=content[start_byte:end_byte],
        extra_headers={
            "Content-Range": content_range,
            "HTTP_CONTENT_RANGE": content_range,
        },
        extra_fields={"X-Upload-ID": upload_identifer},
    )

