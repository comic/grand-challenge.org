import uuid

import pytest

from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile
from grandchallenge.subdomains.utils import reverse
from tests.jqfileupload_tests.utils import (
    create_upload_file_request,
    load_test_data,
)


@pytest.mark.django_db
def test_single_chunk_api(client):
    filename = "test.bin"

    response = create_upload_file_request(
        rf=client, filename=filename, url=reverse("api:staged-file-list")
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
