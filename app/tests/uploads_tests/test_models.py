import pytest
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
    presigned_url = upload_file.get_presigned_url(part_number=0)
    assert presigned_url != ""

    # PUT the file
    response = put(presigned_url, data=b"123")
    assert response.status_code == 200
    assert response.headers["ETag"] != ""

    # Finish the upload
    upload_file.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 0}]
    )
    upload_file.refresh_from_db()
    assert upload_file.status == UserUploadFile.StatusChoices.COMPLETED
