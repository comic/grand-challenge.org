import pytest

from django.test import Client, RequestFactory

from grandchallenge.jqfileupload.filters import reject_duplicate_filenames
from grandchallenge.jqfileupload.widgets.uploader import AjaxUploadWidget
from tests.factories import SUPER_SECURE_TEST_PASSWORD, UserFactory
from tests.jqfileupload_tests.external_test_support import UploadSession


@pytest.mark.django_db
def test_upload_duplicate_images(client):
    user = UserFactory()
    client.login(user=user.username, password=SUPER_SECURE_TEST_PASSWORD)

    widget1 = AjaxUploadWidget(upload_validators=(reject_duplicate_filenames,))
    widget2 = AjaxUploadWidget(upload_validators=(reject_duplicate_filenames,))

    upload_session = UploadSession(test_upload_duplicate_images)
    upload_session2 = UploadSession(test_upload_duplicate_images)

    content = b"0123456789" * int(1e6)

    response = widget1.handle_ajax(
        upload_session.single_chunk_upload(
            client=client,
            filename="test_duplicate_filename.txt",
            content=content,
        )
    )
    assert response.status_code == 200

    response = widget1.handle_ajax(
        upload_session.single_chunk_upload(
            client=client,
            filename="test_duplicate_filename.txt",
            content=content,
        )
    )
    assert response.status_code == 403

    response = widget1.handle_ajax(
        upload_session.single_chunk_upload(
            client=client,
            filename="test_different_filename.txt",
            content=b"123456789",
        )
    )
    assert response.status_code == 200

    # Should work for the second session!
    response = widget1.handle_ajax(
        upload_session2.single_chunk_upload(
            client=client,
            filename="test_duplicate_filename.txt",
            content=b"123456789",
        )
    )
    assert response.status_code == 200

    # Multi chunk uploads should not be special!
    requests = upload_session.multi_chunk_upload(
        client=client,
        filename="test_duplicate_filename.txt",
        content=content,
        chunks=10,
    )
    responses = [widget1.handle_ajax(r) for r in requests]
    assert all(response.status_code == 403 for response in responses)

    requests = upload_session.multi_chunk_upload(
        client=client,
        filename="test_new_duplicate_filename.txt",
        content=content,
        chunks=10,
    )
    responses = [widget1.handle_ajax(r) for r in requests]
    assert all(response.status_code == 200 for response in responses)

    # Uploading the same file to another widget with the same
    # csrf_token should work
    requests = upload_session.multi_chunk_upload(
        client=client,
        filename="test_new_duplicate_filename.txt",
        content=content,
        chunks=10,
    )
    responses = [widget2.handle_ajax(r) for r in requests]
    assert all(response.status_code == 200 for response in responses)
