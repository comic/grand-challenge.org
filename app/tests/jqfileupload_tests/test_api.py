import uuid
from io import BytesIO

import pytest
from rest_framework.authtoken.models import Token

from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile
from grandchallenge.subdomains.utils import reverse
from tests.factories import UserFactory
from tests.jqfileupload_tests.utils import (
    create_upload_file_request,
    load_test_data,
    generate_new_upload_id,
    create_partial_upload_file_request,
)


@pytest.mark.django_db
def test_single_chunk_api(client):
    filename = "test.bin"
    token = Token.objects.create(user=UserFactory())

    response = create_upload_file_request(
        rf=client,
        filename=filename,
        url=reverse("api:staged-file-list"),
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )

    assert response.status_code == 201

    parsed_json = response.json()

    assert parsed_json[0]["filename"] == filename
    assert "uuid" in parsed_json[0]
    assert "extra_attrs" in parsed_json[0]
    staged_file = StagedAjaxFile(uuid.UUID(parsed_json[0]["uuid"]))
    with staged_file.open() as f:
        staged_content = f.read()
    assert staged_content == load_test_data()


@pytest.mark.django_db
def test_single_upload_api(client):
    filename = "test.bin"
    content = load_test_data()
    token = Token.objects.create(user=UserFactory())

    response = client.post(
        path=reverse("api:staged-file-list"),
        data={filename: BytesIO(content)},
        format="multipart",
        HTTP_AUTHORIZATION=f"Token {token}",
    )

    assert response.status_code == 201

    parsed_json = response.json()

    assert len(parsed_json) == 1
    assert parsed_json[0]["filename"] == filename
    assert "uuid" in parsed_json[0]
    assert "extra_attrs" in parsed_json[0]
    staged_file = StagedAjaxFile(uuid.UUID(parsed_json[0]["uuid"]))
    with staged_file.open() as f:
        staged_content = f.read()
    assert staged_content == load_test_data()


@pytest.mark.django_db
def test_rfc7233_implementation_api(client):
    content = load_test_data()
    upload_id = generate_new_upload_id(
        test_rfc7233_implementation_api, content
    )
    url = reverse("api:staged-file-list")
    token = Token.objects.create(user=UserFactory())

    part_1_response = create_partial_upload_file_request(
        client,
        upload_id,
        content,
        0,
        10,
        url=url,
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert part_1_response.status_code == 201

    part_2_response = create_partial_upload_file_request(
        client,
        upload_id,
        content,
        10,
        len(content) // 2,
        url=url,
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert part_2_response.status_code == 201

    part_3_response = create_partial_upload_file_request(
        client,
        upload_id,
        content,
        len(content) // 2,
        len(content),
        url=url,
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert part_3_response.status_code == 201

    parsed_json = part_3_response.json()
    staged_file = StagedAjaxFile(uuid.UUID(parsed_json[0]["uuid"]))

    with staged_file.open() as f:
        staged_content = f.read()

    assert len(staged_content) == len(content)
    assert hash(staged_content) == hash(content)
    assert staged_content == content


@pytest.mark.django_db
def test_wrong_upload_headers(client):
    url = reverse("api:staged-file-list")
    token = Token.objects.create(user=UserFactory())

    response = create_upload_file_request(
        client,
        csrf_token=None,
        url=url,
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert response.status_code == 400
    assert response.json()[0]["csrf"][0] == "This field may not be null."

    response = create_upload_file_request(
        client,
        url=url,
        method="put",
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert response.status_code == 405


@pytest.mark.django_db
def test_wrong_upload_headers_rfc7233_api(client):
    content = load_test_data()
    upload_id = generate_new_upload_id(
        test_wrong_upload_headers_rfc7233_api, content
    )
    url = reverse("api:staged-file-list")
    token = Token.objects.create(user=UserFactory())

    response = create_partial_upload_file_request(
        client,
        upload_id,
        content,
        0,
        10,
        url=url,
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert response.status_code == 201

    response = create_partial_upload_file_request(
        client,
        None,
        content,
        0,
        10,
        url=url,
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert response.status_code == 400

    response = create_partial_upload_file_request(
        client,
        upload_id,
        content,
        0,
        10,
        url=url,
        http_content_range="corrupted data: 54343-3223/21323",
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert response.status_code == 400

    response = create_partial_upload_file_request(
        client,
        upload_id,
        content,
        0,
        10,
        url=url,
        http_content_range="bytes 54343-3223/21323",
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert response.status_code == 400

    response = create_partial_upload_file_request(
        client,
        upload_id,
        content,
        0,
        10,
        url=url,
        http_content_range="bytes 54343-3223/*",
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert response.status_code == 400

    response = create_partial_upload_file_request(
        client,
        upload_id,
        content,
        0,
        10,
        url=url,
        http_content_range="bytes 1000-3000/2000",
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert response.status_code == 400

    response = create_partial_upload_file_request(
        client,
        upload_id,
        content,
        0,
        10,
        url=url,
        http_content_range="bytes 1000-2000/*",
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert response.status_code == 400

    response = create_partial_upload_file_request(
        client,
        "a" * 1000,
        content,
        0,
        10,
        url=url,
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_inconsistent_chunks_rfc7233(client):
    content = load_test_data()
    url = reverse("api:staged-file-list")
    token = Token.objects.create(user=UserFactory())

    # Overlapping chunks
    upload_id = generate_new_upload_id(
        test_inconsistent_chunks_rfc7233, content
    )
    part_1 = create_partial_upload_file_request(
        client,
        upload_id,
        content,
        0,
        10,
        url=url,
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert part_1.status_code == 201
    part_2 = create_partial_upload_file_request(
        client,
        upload_id,
        content,
        5,
        15,
        url=url,
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert part_2.status_code == 400

    # Inconsistent filenames
    upload_id += "x"
    part_1 = create_partial_upload_file_request(
        client,
        upload_id,
        content,
        0,
        10,
        filename="a",
        url=url,
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert part_1.status_code == 201
    part_2 = create_partial_upload_file_request(
        client,
        upload_id,
        content,
        10,
        20,
        filename="b",
        url=url,
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert part_2.status_code == 400

    # Inconsistent total size
    upload_id += "x"
    part_1 = create_partial_upload_file_request(
        client,
        upload_id,
        content[:20],
        0,
        10,
        url=url,
        http_content_range="bytes 0-9/20",
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert part_1.status_code == 201
    part_2 = create_partial_upload_file_request(
        client,
        upload_id,
        content[:20],
        10,
        20,
        url=url,
        http_content_range="bytes 10-19/30",
        extra_headers={"HTTP_AUTHORIZATION": f"Token {token}"},
    )
    assert part_2.status_code == 400
