from io import BytesIO

import pytest

from grandchallenge.subdomains.utils import reverse
from tests.factories import UserFactory
from tests.jqfileupload_tests.utils import load_test_data
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_create_permission(client):
    filename = "test.bin"
    content = load_test_data()

    tests = ((UserFactory(), 201), (None, 401))

    for test in tests:
        response = get_view_for_user(
            client=client,
            method=client.post,
            user=test[0],
            url=reverse("api:staged-file-list"),
            data={filename: BytesIO(content)},
            format="multipart",
        )

        assert response.status_code == test[1]


@pytest.mark.django_db
def test_read_permission(client):
    u1, u2 = UserFactory(), UserFactory()
    filename = "test.bin"
    content = load_test_data()

    created_file = get_view_for_user(
        client=client,
        method=client.post,
        user=u1,
        url=reverse("api:staged-file-list"),
        data={filename: BytesIO(content)},
        format="multipart",
    )

    assert created_file.status_code == 201

    # Users should be able to see their own files
    response = get_view_for_user(
        client=client,
        user=u1,
        url=reverse("api:staged-file-list"),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1

    # Other users should not be able to see other files
    response = get_view_for_user(
        client=client,
        user=u2,
        url=reverse("api:staged-file-list"),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0
