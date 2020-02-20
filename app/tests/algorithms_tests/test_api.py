from urllib.parse import urlparse

import pytest

from tests.algorithms_tests.factories import (
    AlgorithmJobFactory,
    AlgorithmResultFactory,
)
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.factories import ImageFactory, UserFactory
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


@pytest.mark.django_db
def test_keys_used_in_algorithm_session_js(client):
    """All of these values are used in algorithms/js/session.js"""
    u = UserFactory()
    i = ImageFactory()
    j = AlgorithmJobFactory(creator=u, image=i)
    r = AlgorithmResultFactory(job=j)
    s = RawImageUploadSessionFactory(creator=u, algorithm_result=r)

    # Result API
    response = get_view_for_user(client=client, url=r.api_url, user=u)
    assert response.status_code == 200
    # Unsecure urls are always returned in testing
    assert response.json()["import_session"] == s.api_url.replace(
        "https:", "http:"
    )

    # Session API
    response = get_view_for_user(client=client, url=s.api_url, user=u)
    assert response.status_code == 200
    assert response.json()["status"] == "Queued"
    assert response.json()["api_url"] == s.api_url
    assert response.json()["image_set"] == []

    # Job API
    response = get_view_for_user(client=client, url=j.api_url, user=u)
    assert response.status_code == 200
    assert response.json()["status"] == "Queued"
    assert response.json()["api_url"] == j.api_url

    # Image API
    response = get_view_for_user(client=client, url=i.api_url, user=u)
    assert response.status_code == 200
    assert response.json()["job_set"] == [j.api_url.replace("https:", "http:")]
