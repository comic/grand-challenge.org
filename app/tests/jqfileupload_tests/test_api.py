import pytest

from grandchallenge.subdomains.utils import reverse
from tests.jqfileupload_tests.utils import create_upload_file_request


@pytest.mark.django_db
def test_single_chunk_api(client):
    filename = "test.bin"

    response = create_upload_file_request(
        rf=client, filename=filename, url=reverse("api:staged-file-list")
    )

    assert response.status_code == 201
