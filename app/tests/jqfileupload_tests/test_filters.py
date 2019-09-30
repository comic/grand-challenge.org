import pytest
from rest_framework.authtoken.models import Token

from grandchallenge.jqfileupload.filters import reject_duplicate_filenames
from grandchallenge.jqfileupload.widgets.uploader import AjaxUploadWidget
from tests.factories import UserFactory
from tests.jqfileupload_tests.external_test_support import UploadSession


@pytest.mark.django_db
def test_upload_duplicate_images(client):
    auth_token = Token.objects.create(user=UserFactory())

    widget1 = AjaxUploadWidget(upload_validators=(reject_duplicate_filenames,))
    widget2 = AjaxUploadWidget(upload_validators=(reject_duplicate_filenames,))

    upload_session = UploadSession(
        test_upload_duplicate_images, auth_token=auth_token
    )
    upload_session2 = UploadSession(
        test_upload_duplicate_images, auth_token=auth_token
    )

    content = b"0123456789" * int(1e6)

    response = upload_session.single_chunk_upload(
        client=client, filename="test_duplicate_filename.txt", content=content
    )
    assert response.status_code == 201

    response = upload_session.single_chunk_upload(
        client=client, filename="test_duplicate_filename.txt", content=content
    )
    assert response.status_code == 403

    response = upload_session.single_chunk_upload(
        client=client,
        filename="test_different_filename.txt",
        content=b"123456789",
    )
    assert response.status_code == 201

    # Should work for the second session!
    response = upload_session2.single_chunk_upload(
        client=client,
        filename="test_duplicate_filename.txt",
        content=b"123456789",
    )
    assert response.status_code == 201

    # Multi chunk uploads should not be special!
    responses = upload_session.multi_chunk_upload(
        client=client,
        filename="test_duplicate_filename.txt",
        content=content,
        chunks=10,
    )
    assert all(response.status_code == 403 for response in responses)

    responses = upload_session.multi_chunk_upload(
        client=client,
        filename="test_new_duplicate_filename.txt",
        content=content,
        chunks=10,
    )
    assert all(response.status_code == 201 for response in responses)

    # Uploading the same file to another widget with the same
    # csrf_token should work
    responses = upload_session.multi_chunk_upload(
        client=client,
        filename="test_new_duplicate_filename.txt",
        content=content,
        chunks=10,
    )
    assert all(response.status_code == 201 for response in responses)
