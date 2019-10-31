import os
import random
import time

from django.test import RequestFactory


def load_test_data():
    with open(
        os.path.join(os.path.dirname(__file__), "testdata", "rnddata"), "rb"
    ) as f:
        return f.read()


def generate_new_upload_id(sender, content):
    return f"{id(sender)}_{hash(content)}_{time.time()}_{random.random()}"


def create_upload_file_request(
    rf: RequestFactory,
    filename: str = "test.bin",
    boundary: str = "RandomBoundaryFTWBlablablablalba8923475278934578",
    content: bytes = None,
    extra_fields: dict = None,
    extra_headers: dict = None,
    url: str = "/ajax",
    method: str = "post",
):
    if extra_headers is None:
        extra_headers = {}

    if extra_fields is None:
        extra_fields = {}

    if content is None:
        content = load_test_data()

    # Basic request
    data = (
        f"""
--{boundary}\r
Content-Disposition: form-data; name="files[]"; filename="{filename}"\r
Content-Type: application/octet-stream\r
\r
""".lstrip().encode()
        + content
        + f"""\r
--{boundary}--""".encode()
    )
    # Add additional fields
    for key, value in extra_fields.items():
        extra_field_data = f"""
--{boundary}\r
Content-Disposition: form-data; name="{key}"\r
\r
{value}\r
""".lstrip().encode()
        data = extra_field_data + data
    return getattr(rf, method)(
        url,
        data=data,
        content_type=f"multipart/form-data; boundary={boundary}",
        **extra_headers,
    )


def create_partial_upload_file_request(
    rf: RequestFactory,
    upload_identifer: str,
    content: bytes,
    start_byte: int,
    end_byte: int,
    filename: str = "test.bin",
    url: str = "/ajax",
    http_content_range=None,
    extra_headers=None,
):
    content_range = f"bytes {start_byte}-{end_byte - 1}/{len(content)}"

    if http_content_range is None:
        http_content_range = content_range

    if extra_headers is None:
        extra_headers = {}

    extra_fields = {}
    if upload_identifer:
        extra_fields.update({"X-Upload-ID": upload_identifer})

    return create_upload_file_request(
        rf,
        filename=filename,
        content=content[start_byte:end_byte],
        extra_headers={
            "Content-Range": content_range,
            "HTTP_CONTENT_RANGE": http_content_range,
            **extra_headers,
        },
        extra_fields=extra_fields,
        url=url,
    )
