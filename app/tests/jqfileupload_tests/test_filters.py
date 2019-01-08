import pytest

from django.test import Client, RequestFactory

from grandchallenge.jqfileupload.filters import reject_duplicate_filenames
from grandchallenge.jqfileupload.widgets.uploader import AjaxUploadWidget
from tests.jqfileupload_tests.external_test_support import UploadSession


@pytest.mark.django_db
def test_upload_duplicate_images(rf: RequestFactory):
    widget1 = AjaxUploadWidget(
        ajax_target_path="/ajax",
        upload_validators=(reject_duplicate_filenames,),
    )
    widget2 = AjaxUploadWidget(
        ajax_target_path="/ajax2",
        upload_validators=(reject_duplicate_filenames,),
    )

    upload_session = UploadSession(test_upload_duplicate_images)
    upload_session2 = UploadSession(test_upload_duplicate_images)

    content = b"0123456789" * int(1e6)

    response = widget1.handle_ajax(
        upload_session.single_chunk_upload(
            rf,
            "test_duplicate_filename.txt",
            content,
            widget1.ajax_target_path,
        )
    )
    assert response.status_code == 200

    response = widget1.handle_ajax(
        upload_session.single_chunk_upload(
            rf,
            "test_duplicate_filename.txt",
            content,
            widget1.ajax_target_path,
        )
    )
    assert response.status_code == 403

    response = widget1.handle_ajax(
        upload_session.single_chunk_upload(
            rf,
            "test_different_filename.txt",
            b"123456789",
            widget1.ajax_target_path,
        )
    )
    assert response.status_code == 200

    # Should work for the second session!
    response = widget1.handle_ajax(
        upload_session2.single_chunk_upload(
            rf,
            "test_duplicate_filename.txt",
            b"123456789",
            widget1.ajax_target_path,
        )
    )
    assert response.status_code == 200

    # Multi chunk uploads should not be special!
    requests = upload_session.multi_chunk_upload(
        rf,
        "test_duplicate_filename.txt",
        content,
        widget1.ajax_target_path,
        chunks=10,
    )
    responses = [widget1.handle_ajax(r) for r in requests]
    assert all(response.status_code == 403 for response in responses)

    requests = upload_session.multi_chunk_upload(
        rf,
        "test_new_duplicate_filename.txt",
        content,
        widget1.ajax_target_path,
        chunks=10,
    )
    responses = [widget1.handle_ajax(r) for r in requests]
    assert all(response.status_code == 200 for response in responses)

    # Uploading the same file to another widget with the same
    # csrf_token should work
    requests = upload_session.multi_chunk_upload(
        rf,
        "test_new_duplicate_filename.txt",
        content,
        widget2.ajax_target_path,
        chunks=10,
    )
    responses = [widget2.handle_ajax(r) for r in requests]
    assert all(response.status_code == 200 for response in responses)
