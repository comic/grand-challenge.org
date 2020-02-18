from urllib.parse import urlparse

import pytest

from tests.algorithms_tests.factories import AlgorithmResultFactory
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_job_detail(client):
    user = UserFactory()
    result = AlgorithmResultFactory(job__creator=user)
    job = result.job
    response = get_view_for_user(
        viewname="api:algorithms-job-detail",
        client=client,
        user=user,
        reverse_kwargs={"pk": result.job.pk},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert job.status == job.PENDING
    assert response.json()["status"] == "Queued"
    assert (
        urlparse(response.json()["result"]).path
        == urlparse(result.api_url).path
    )
