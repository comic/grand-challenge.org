import pytest
from requests import put

from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_user_upload_flow(client):
    # Create User Upload
    u = UserFactory()
    filename = "foo.bat"

    response = get_view_for_user(
        client=client, viewname="api:upload-list", method=client.post, user=u,
    )
    assert response.status_code == 201
    upload = response.json()

    # Create User Upload File
    response = get_view_for_user(
        client=client,
        viewname="api:uploads-file-list",
        method=client.post,
        data={"upload": upload["pk"], "filename": filename},
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

    # Get the presigned url
    response = get_view_for_user(
        client=client,
        viewname="api:uploads-file-generate-presigned-url",
        reverse_kwargs={"pk": upload_file["pk"]},
        method=client.patch,
        data={"part_number": part_number},
        content_type="application/json",
        user=u,
    )
    assert response.status_code == 200
    presigned_url = response.json()["presigned_url"]
    assert presigned_url != ""

    # PUT the file
    response = put(presigned_url, data=content)
    assert response.status_code == 200
    assert response.headers["ETag"] != ""

    # Add the part to the list of uploads
    parts.append(
        {"e_tag": response.headers["ETag"], "part_number": part_number}
    )

    # Finish the upload
    response = get_view_for_user(
        client=client,
        viewname="api:uploads-file-complete-multipart-upload",
        reverse_kwargs={"pk": upload_file["pk"]},
        method=client.patch,
        data={"parts": parts},
        content_type="application/json",
        user=u,
    )
    assert response.status_code == 200
    upload = response.json()

    assert upload["status"] == "Completed"
