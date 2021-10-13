import pytest
from requests import put

from grandchallenge.uploads.models import UserUpload
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_user_upload_flow(client):
    # Create User Upload
    u = UserFactory()
    filename = "foo.bat"

    # Create User Upload
    response = get_view_for_user(
        client=client,
        viewname="api:upload-list",
        method=client.post,
        data={"filename": filename},
        content_type="application/json",
        user=u,
    )
    assert response.status_code == 201
    upload_file = response.json()

    assert upload_file["status"] == "Initialized"

    # For each file part
    part_number = 1
    content = b"123"  # slice of file data
    parts = []

    # Get the presigned urls
    response = get_view_for_user(
        client=client,
        viewname="api:upload-generate-presigned-urls",
        reverse_kwargs={
            "pk": upload_file["pk"],
            "s3_upload_id": upload_file["s3_upload_id"],
        },
        method=client.patch,
        data={"part_numbers": [part_number]},
        content_type="application/json",
        user=u,
    )
    assert response.status_code == 200
    presigned_urls = response.json()["presigned_urls"]
    assert presigned_urls != {}

    # PUT the file
    response = put(presigned_urls[str(part_number)], data=content)
    assert response.status_code == 200
    assert response.headers["ETag"] != ""

    # Add the part to the list of uploads
    parts.append({"ETag": response.headers["ETag"], "PartNumber": part_number})

    # Finish the upload
    response = get_view_for_user(
        client=client,
        viewname="api:upload-complete-multipart-upload",
        reverse_kwargs={
            "pk": upload_file["pk"],
            "s3_upload_id": upload_file["s3_upload_id"],
        },
        method=client.patch,
        data={"parts": parts},
        content_type="application/json",
        user=u,
    )
    assert response.status_code == 200
    upload = response.json()

    assert upload["status"] == "Completed"


@pytest.mark.django_db
def test_create_multipart_upload(client):
    # https://uppy.io/docs/aws-s3-multipart/#createMultipartUpload-file
    u = UserFactory()

    response = get_view_for_user(
        client=client,
        viewname="api:upload-list",
        method=client.post,
        data={"filename": "foo.bat"},
        content_type="application/json",
        user=u,
    )

    assert response.status_code == 201
    upload_file = response.json()

    assert upload_file["status"] == "Initialized"
    assert upload_file["s3_upload_id"] != ""
    assert upload_file["key"] == f"uploads/{u.pk}/{upload_file['pk']}"
    assert upload_file["filename"] == "foo.bat"


@pytest.mark.django_db
def test_create_multipart_upload_bad_filename(client):
    # https://uppy.io/docs/aws-s3-multipart/#createMultipartUpload-file
    u = UserFactory()

    response = get_view_for_user(
        client=client,
        viewname="api:upload-list",
        method=client.post,
        data={"filename": "../../foo.bat"},
        content_type="application/json",
        user=u,
    )

    assert response.status_code == 400
    assert response.json() == {
        "filename": ["../../foo.bat is not a valid filename"]
    }


@pytest.mark.django_db
def test_list_parts(client):
    # https://uppy.io/docs/aws-s3-multipart/#listParts-file-uploadId-key
    u = UserFactory()
    upload = UserUpload.objects.create(creator=u)
    url = upload.generate_presigned_url(part_number=1)
    uploaded_part = put(url, data=b"123")

    response = get_view_for_user(
        client=client,
        viewname="api:upload-list-parts",
        reverse_kwargs={"pk": upload.pk, "s3_upload_id": upload.s3_upload_id},
        content_type="application/json",
        user=u,
    )

    assert response.status_code == 200

    assert response.json()["pk"] == str(upload.pk)
    assert response.json()["s3_upload_id"] == upload.s3_upload_id
    assert response.json()["key"] == upload.key

    parts = response.json()["parts"]
    del parts[0]["LastModified"]
    assert parts == [
        {"ETag": uploaded_part.headers["ETag"], "PartNumber": 1, "Size": 3}
    ]


@pytest.mark.django_db
def test_prepare_upload_parts(client):
    # https://uppy.io/docs/aws-s3-multipart/#prepareUploadParts-file-partData
    u = UserFactory()
    upload = UserUpload.objects.create(creator=u)

    response = get_view_for_user(
        client=client,
        viewname="api:upload-generate-presigned-urls",
        reverse_kwargs={"pk": upload.pk, "s3_upload_id": upload.s3_upload_id},
        method=client.patch,
        data={"part_numbers": [35, 42, 128]},
        content_type="application/json",
        user=u,
    )

    assert response.status_code == 200

    assert response.json()["pk"] == str(upload.pk)
    assert response.json()["s3_upload_id"] == upload.s3_upload_id
    assert response.json()["key"] == upload.key

    presigned_urls = response.json()["presigned_urls"]

    assert set(presigned_urls.keys()) == {"35", "42", "128"}


@pytest.mark.django_db
def test_abort_multipart_upload(client):
    # https://uppy.io/docs/aws-s3-multipart/#abortMultipartUpload-file-uploadId-key
    u = UserFactory()
    upload = UserUpload.objects.create(creator=u)

    response = get_view_for_user(
        client=client,
        viewname="api:upload-abort-multipart-upload",
        reverse_kwargs={"pk": upload.pk, "s3_upload_id": upload.s3_upload_id},
        method=client.patch,
        data={},
        content_type="application/json",
        user=u,
    )

    assert response.status_code == 200

    assert response.json()["pk"] == str(upload.pk)
    assert response.json()["s3_upload_id"] == ""
    assert response.json()["key"] == upload.key
    assert response.json()["status"] == "Aborted"


@pytest.mark.django_db
def test_complete_multipart_upload(client):
    # https://uppy.io/docs/aws-s3-multipart/#completeMultipartUpload-file-uploadId-key-parts
    u = UserFactory()
    upload = UserUpload.objects.create(creator=u)
    url = upload.generate_presigned_url(part_number=1)
    uploaded_part = put(url, data=b"123")

    response = get_view_for_user(
        client=client,
        viewname="api:upload-complete-multipart-upload",
        reverse_kwargs={"pk": upload.pk, "s3_upload_id": upload.s3_upload_id},
        method=client.patch,
        data={
            "parts": [{"ETag": uploaded_part.headers["ETag"], "PartNumber": 1}]
        },
        content_type="application/json",
        user=u,
    )
    assert response.status_code == 200

    assert response.json()["pk"] == str(upload.pk)
    assert response.json()["s3_upload_id"] == upload.s3_upload_id
    assert response.json()["key"] == upload.key
    assert response.json()["status"] == "Completed"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "action",
    [
        "list-parts",
        "generate-presigned-urls",
        "abort-multipart-upload",
        "complete-multipart-upload",
    ],
)
def test_url_pattern(client, action):
    # On the frontend we construct the URL with
    # url = `{api_root}/uploads/{upload_pk}/{upload_s3_upload_id}/{action}`
    # Check that this matches
    u = UserFactory()
    upload = UserUpload.objects.create(creator=u)

    url = f"/api/v1/uploads/{upload.pk}/{upload.s3_upload_id}/{action}/"

    response = get_view_for_user(
        client=client,
        url=url,
        method=client.get if action == "list-parts" else client.patch,
        data={},
        content_type="application/json",
        user=u,
    )
    assert response.status_code != 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "action",
    [
        "list-parts",
        "generate-presigned-urls",
        "abort-multipart-upload",
        "complete-multipart-upload",
    ],
)
def test_upload_id_checks(client, action):
    # 404 should be returned if the upload id in the url does
    # not match the one tracked by our object
    u = UserFactory()
    upload = UserUpload.objects.create(creator=u)

    url = f"/api/v1/uploads/{upload.pk}/1{upload.s3_upload_id}/{action}/"

    response = get_view_for_user(
        client=client,
        url=url,
        method=client.get if action == "list-parts" else client.patch,
        data={},
        content_type="application/json",
        user=u,
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_prepare_upload_parts_limit_reached(client, settings):
    # https://uppy.io/docs/aws-s3-multipart/#prepareUploadParts-file-partData
    u = UserFactory()
    upload = UserUpload.objects.create(creator=u)
    settings.UPLOADS_MAX_SIZE_UNVERIFIED = 0

    response = get_view_for_user(
        client=client,
        viewname="api:upload-generate-presigned-urls",
        reverse_kwargs={"pk": upload.pk, "s3_upload_id": upload.s3_upload_id},
        method=client.patch,
        data={"part_numbers": [35, 42, 128]},
        content_type="application/json",
        user=u,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Upload limit reached"
