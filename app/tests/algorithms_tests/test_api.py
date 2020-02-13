from urllib.parse import urlparse

import pytest

from tests.algorithms_tests.factories import (
    AlgorithmJobFactory,
    AlgorithmResultFactory,
)
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_job_list(client):
    u = UserFactory()
    j = AlgorithmJobFactory(creator=u)
    r = AlgorithmResultFactory(job=j)
    response = get_view_for_user(
        viewname="api:algorithms-job-list",
        client=client,
        user=u,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert j.status == 0
    assert response.json()["results"][0]["status"] == "Queued"
    assert (
        urlparse(response.json()["results"][0]["result"]).path
        == urlparse(r.api_url).path
    )
