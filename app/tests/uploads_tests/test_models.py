import pytest
from django.conf import settings
from requests import put

from grandchallenge.uploads.models import UserUpload, UserUploadFile
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_upload_flow():
    # Create User Upload
    u = UserFactory()
    filename = "foo.bat"
    upload = UserUpload.objects.create(creator=u)

    # Create User Upload File
    upload_file = UserUploadFile.objects.create(
        upload=upload, filename=filename
    )
    assert upload_file.status == UserUploadFile.StatusChoices.INITIALIZED
    assert upload_file.s3_upload_id != ""

    # Get the presigned url
    presigned_url = upload_file.generate_presigned_url(part_number=0)
    assert presigned_url != ""

    # PUT the file
    response = put(presigned_url, data=b"123")
    assert response.status_code == 200
    assert response.headers["ETag"] != ""

    # Finish the upload
    upload_file.complete_multipart_upload(
        parts=[{"e_tag": response.headers["ETag"], "part_number": 0}]
    )
    assert upload_file.status == UserUploadFile.StatusChoices.COMPLETED


def test_create_multipart_upload():
    upload = UserUpload()
    file = UserUploadFile(upload=upload)

    assert file.s3_upload_id == ""
    assert file.status == UserUploadFile.StatusChoices.PENDING

    file.create_multipart_upload()

    assert file.s3_upload_id != ""
    assert file.status == UserUploadFile.StatusChoices.INITIALIZED
    assert file.key == f"uploads/{upload.pk}/{file.pk}"


def test_generate_presigned_urls():
    upload = UserUpload()
    file = UserUploadFile(upload=upload)
    file.create_multipart_upload()

    presigned_urls = file.generate_presigned_urls(part_numbers=[1, 13, 26])

    assert set(presigned_urls.keys()) == {1, 13, 26}
    assert presigned_urls[1].startswith(
        f"{settings.UPLOADS_S3_ENDPOINT_URL}/{file.bucket}/{file.key}?uploadId={file.s3_upload_id}&partNumber=1&"
    )
    assert presigned_urls[13].startswith(
        f"{settings.UPLOADS_S3_ENDPOINT_URL}/{file.bucket}/{file.key}?uploadId={file.s3_upload_id}&partNumber=13&"
    )
    assert presigned_urls[26].startswith(
        f"{settings.UPLOADS_S3_ENDPOINT_URL}/{file.bucket}/{file.key}?uploadId={file.s3_upload_id}&partNumber=26&"
    )


def test_abort_multipart_upload():
    upload = UserUpload()
    file = UserUploadFile(upload=upload)
    file.create_multipart_upload()

    assert file.status == UserUploadFile.StatusChoices.INITIALIZED
    assert file.s3_upload_id != ""

    file.abort_multipart_upload()

    assert file.status == UserUploadFile.StatusChoices.ABORTED
    assert file.s3_upload_id == ""


def test_list_parts():
    upload = UserUpload()
    file = UserUploadFile(upload=upload)
    file.create_multipart_upload()
    url = file.generate_presigned_url(part_number=1)
    response = put(url, data=b"123")

    parts = file.list_parts()

    assert len(parts) == 1
    assert parts[0]["ETag"] == response.headers["ETag"]
    assert parts[0]["Size"] == 3
    assert parts[0]["PartNumber"] == 1


def test_list_parts_truncation():
    upload = UserUpload()
    file = UserUploadFile(upload=upload)
    file.create_multipart_upload()
    presigned_urls = file.generate_presigned_urls(part_numbers=[1, 2])
    responses = {}
    for part_number, url in presigned_urls.items():
        responses[part_number] = put(url, data=b"123")

    file.LIST_MAX_PARTS = 1
    parts = file.list_parts()

    assert len(parts) == 2
    assert parts[0]["ETag"] == responses[1].headers["ETag"]
    assert parts[0]["Size"] == 3
    assert parts[0]["PartNumber"] == 1
    assert parts[1]["ETag"] == responses[2].headers["ETag"]
    assert parts[1]["Size"] == 3
    assert parts[1]["PartNumber"] == 2
