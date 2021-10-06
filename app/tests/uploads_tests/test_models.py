import pytest
from django.conf import settings
from requests import put

from grandchallenge.uploads.models import UserUpload
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_upload_flow():
    # Create User Upload
    u = UserFactory()
    filename = "foo.bat"

    # Create User Upload File
    upload = UserUpload.objects.create(creator=u, filename=filename)
    assert upload.status == UserUpload.StatusChoices.INITIALIZED
    assert upload.s3_upload_id != ""

    # Get the presigned url
    presigned_url = upload.generate_presigned_url(part_number=0)
    assert presigned_url != ""

    # PUT the file
    response = put(presigned_url, data=b"123")
    assert response.status_code == 200
    assert response.headers["ETag"] != ""

    # Finish the upload
    upload.complete_multipart_upload(
        parts=[{"e_tag": response.headers["ETag"], "part_number": 0}]
    )
    assert upload.status == UserUpload.StatusChoices.COMPLETED


def test_create_multipart_upload():
    upload = UserUpload()

    assert upload.s3_upload_id == ""
    assert upload.status == UserUpload.StatusChoices.PENDING

    upload.create_multipart_upload()

    assert upload.s3_upload_id != ""
    assert upload.status == UserUpload.StatusChoices.INITIALIZED
    assert upload.key == f"uploads/{upload.pk}"


def test_generate_presigned_urls():
    upload = UserUpload()
    upload.create_multipart_upload()

    presigned_urls = upload.generate_presigned_urls(part_numbers=[1, 13, 26])

    assert set(presigned_urls.keys()) == {1, 13, 26}
    assert presigned_urls[1].startswith(
        f"{settings.UPLOADS_S3_ENDPOINT_URL}/{upload.bucket}/{upload.key}?uploadId={upload.s3_upload_id}&partNumber=1&"
    )
    assert presigned_urls[13].startswith(
        f"{settings.UPLOADS_S3_ENDPOINT_URL}/{upload.bucket}/{upload.key}?uploadId={upload.s3_upload_id}&partNumber=13&"
    )
    assert presigned_urls[26].startswith(
        f"{settings.UPLOADS_S3_ENDPOINT_URL}/{upload.bucket}/{upload.key}?uploadId={upload.s3_upload_id}&partNumber=26&"
    )


def test_abort_multipart_upload():
    upload = UserUpload()
    upload.create_multipart_upload()

    assert upload.status == UserUpload.StatusChoices.INITIALIZED
    assert upload.s3_upload_id != ""

    upload.abort_multipart_upload()

    assert upload.status == UserUpload.StatusChoices.ABORTED
    assert upload.s3_upload_id == ""


def test_list_parts():
    upload = UserUpload()
    upload.create_multipart_upload()
    url = upload.generate_presigned_url(part_number=1)
    response = put(url, data=b"123")

    parts = upload.list_parts()

    assert len(parts) == 1
    assert parts[0]["ETag"] == response.headers["ETag"]
    assert parts[0]["Size"] == 3
    assert parts[0]["PartNumber"] == 1


def test_list_parts_truncation():
    upload = UserUpload()
    upload.create_multipart_upload()
    presigned_urls = upload.generate_presigned_urls(part_numbers=[1, 2])
    responses = {}
    for part_number, url in presigned_urls.items():
        responses[part_number] = put(url, data=b"123")

    upload.LIST_MAX_PARTS = 1
    parts = upload.list_parts()

    assert len(parts) == 2
    assert parts[0]["ETag"] == responses[1].headers["ETag"]
    assert parts[0]["Size"] == 3
    assert parts[0]["PartNumber"] == 1
    assert parts[1]["ETag"] == responses[2].headers["ETag"]
    assert parts[1]["Size"] == 3
    assert parts[1]["PartNumber"] == 2
