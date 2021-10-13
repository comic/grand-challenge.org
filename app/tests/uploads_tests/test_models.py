import pytest
from django.conf import settings
from requests import put

from grandchallenge.uploads.models import UserUpload
from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.factories import UserFactory
from tests.verification_tests.factories import VerificationFactory


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
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 0}]
    )
    assert upload.status == UserUpload.StatusChoices.COMPLETED


def test_create_multipart_upload():
    user = UserFactory.build()
    upload = UserUpload(creator=user)

    assert upload.s3_upload_id == ""
    assert upload.status == UserUpload.StatusChoices.PENDING

    upload.create_multipart_upload()

    assert upload.s3_upload_id != ""
    assert upload.status == UserUpload.StatusChoices.INITIALIZED
    assert upload.key == f"uploads/{user.pk}/{upload.pk}"


def test_generate_presigned_urls():
    upload = UserUpload(creator=UserFactory.build())
    upload.create_multipart_upload()

    presigned_urls = upload.generate_presigned_urls(part_numbers=[1, 13, 26])

    assert set(presigned_urls.keys()) == {"1", "13", "26"}
    assert presigned_urls["1"].startswith(
        f"{settings.AWS_S3_ENDPOINT_URL}/{upload.bucket}/{upload.key}?uploadId={upload.s3_upload_id}&partNumber=1&"
    )
    assert presigned_urls["13"].startswith(
        f"{settings.AWS_S3_ENDPOINT_URL}/{upload.bucket}/{upload.key}?uploadId={upload.s3_upload_id}&partNumber=13&"
    )
    assert presigned_urls["26"].startswith(
        f"{settings.AWS_S3_ENDPOINT_URL}/{upload.bucket}/{upload.key}?uploadId={upload.s3_upload_id}&partNumber=26&"
    )


def test_abort_multipart_upload():
    upload = UserUpload(creator=UserFactory.build())
    upload.create_multipart_upload()

    assert upload.status == UserUpload.StatusChoices.INITIALIZED
    assert upload.s3_upload_id != ""

    upload.abort_multipart_upload()

    assert upload.status == UserUpload.StatusChoices.ABORTED
    assert upload.s3_upload_id == ""


def test_list_parts():
    upload = UserUpload(creator=UserFactory.build())
    upload.create_multipart_upload()
    url = upload.generate_presigned_url(part_number=1)
    response = put(url, data=b"123")

    parts = upload.list_parts()

    assert len(parts) == 1
    assert parts[0]["ETag"] == response.headers["ETag"]
    assert parts[0]["Size"] == 3
    assert parts[0]["PartNumber"] == 1


def test_list_parts_empty():
    upload = UserUpload(creator=UserFactory.build())
    upload.create_multipart_upload()

    parts = upload.list_parts()

    assert parts == []


def test_list_parts_truncation():
    upload = UserUpload(creator=UserFactory.build())
    upload.create_multipart_upload()
    presigned_urls = upload.generate_presigned_urls(part_numbers=[1, 2])
    responses = {}
    for part_number, url in presigned_urls.items():
        responses[part_number] = put(url, data=b"123")

    upload.LIST_MAX_ITEMS = 1
    parts = upload.list_parts()

    assert len(parts) == 2
    assert parts[0]["ETag"] == responses["1"].headers["ETag"]
    assert parts[0]["Size"] == 3
    assert parts[0]["PartNumber"] == 1
    assert parts[1]["ETag"] == responses["2"].headers["ETag"]
    assert parts[1]["Size"] == 3
    assert parts[1]["PartNumber"] == 2


@pytest.mark.django_db
def test_upload_copy():
    user = UserFactory()
    upload = UserUpload.objects.create(creator=user, filename="test.tar.gz")
    presigned_urls = upload.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b"123")
    upload.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    upload.save()
    ai = AlgorithmImageFactory(creator=user, image=None)

    assert not ai.image

    upload.copy_object(to_field=ai.image)

    assert (
        ai.image.name
        == f"docker/images/algorithms/algorithmimage/{ai.pk}/test.tar.gz"
    )
    assert ai.image.storage.exists(name=ai.image.name)

    with ai.image.open() as f:
        assert f.read() == b"123"


@pytest.mark.django_db
def test_file_deleted_with_object():
    u = UserFactory()
    upload = UserUpload.objects.create(creator=u)
    presigned_urls = upload.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b"123")
    upload.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    upload.save()

    bucket = upload.bucket
    key = upload.key
    assert upload._client.head_object(Bucket=bucket, Key=key)

    UserUpload.objects.filter(pk=upload.pk).delete()

    with pytest.raises(upload._client.exceptions.ClientError):
        upload._client.head_object(Bucket=bucket, Key=key)


@pytest.mark.django_db
def test_incomplete_deleted_with_object():
    u = UserFactory()
    upload = UserUpload.objects.create(creator=u)

    bucket = upload.bucket
    key = upload.key
    assert "Uploads" in upload._client.list_multipart_uploads(
        Bucket=bucket, Prefix=key
    )

    UserUpload.objects.filter(pk=upload.pk).delete()

    assert "Uploads" not in upload._client.list_multipart_uploads(
        Bucket=bucket, Prefix=key
    )


def test_size_of_creators_completed_uploads():
    def upload_files_for_user(user, n=1):
        for _ in range(n):
            ul = UserUpload(creator=user)
            ul.create_multipart_upload()
            presigned_urls = ul.generate_presigned_urls(part_numbers=[1])
            response = put(presigned_urls["1"], data=b"123")
            ul.complete_multipart_upload(
                parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
            )

    u = UserFactory.build(pk=42)
    upload = UserUpload(creator=u)
    upload.LIST_MAX_ITEMS = 1
    initial_upload_size = upload.size_of_creators_completed_uploads

    assert type(initial_upload_size) == int

    upload_files_for_user(user=u, n=upload.LIST_MAX_ITEMS + 1)
    # another users files should not be considered
    upload_files_for_user(user=UserFactory.build(pk=u.pk + 1))

    assert (
        upload.size_of_creators_completed_uploads
        == initial_upload_size + (upload.LIST_MAX_ITEMS + 1) * 3
    )


def test_size_incomplete():
    u = UserFactory.build(pk=42)
    upload = UserUpload(creator=u)
    upload.create_multipart_upload()
    upload.LIST_MAX_ITEMS = 1

    assert upload.size == 0

    parts = [1, 2]
    presigned_urls = upload.generate_presigned_urls(part_numbers=parts)
    for part in parts:
        put(presigned_urls[str(part)], data=b"123")

    assert upload.size == (upload.LIST_MAX_ITEMS + 1) * 3


def test_size_complete():
    u = UserFactory.build(pk=42)
    upload = UserUpload(creator=u)
    upload.create_multipart_upload()

    assert upload.size == 0

    presigned_urls = upload.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b"123")
    upload.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )

    assert upload.size == 3


@pytest.mark.django_db
def test_can_upload_more_unverified(settings):
    upload = UserUpload.objects.create(creator=UserFactory())
    presigned_urls = upload.generate_presigned_urls(part_numbers=[1])
    put(presigned_urls["1"], data=b"123")

    assert upload.can_upload_more is True

    settings.UPLOADS_MAX_SIZE_UNVERIFIED = 2

    assert upload.can_upload_more is False


@pytest.mark.django_db
def test_can_upload_more_verified(settings):
    user = UserFactory()
    upload = UserUpload.objects.create(creator=user)
    presigned_urls = upload.generate_presigned_urls(part_numbers=[1])
    put(presigned_urls["1"], data=b"123")
    settings.UPLOADS_MAX_SIZE_UNVERIFIED = 2

    assert upload.can_upload_more is False

    VerificationFactory(user=user, is_verified=True)

    assert upload.can_upload_more is True

    settings.UPLOADS_MAX_SIZE_VERIFIED = 2

    assert upload.can_upload_more is False


@pytest.mark.django_db
def test_can_upload_more_other_objects(settings):
    user = UserFactory()
    new_upload = UserUpload.objects.create(creator=user)
    settings.UPLOADS_MAX_SIZE_UNVERIFIED = 2

    assert new_upload.can_upload_more is True

    upload = UserUpload.objects.create(creator=user)
    presigned_urls = upload.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b"123")
    upload.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )

    assert upload.can_upload_more is False
    assert new_upload.can_upload_more is False
