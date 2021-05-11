import pytest

from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_job_detail(client):
    user = UserFactory()
    job = AlgorithmJobFactory(creator=user)
    response = get_view_for_user(
        viewname="api:algorithms-job-detail",
        client=client,
        user=user,
        reverse_kwargs={"pk": job.pk},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert job.status == job.PENDING
    assert response.json()["status"] == "Queued"


@pytest.mark.django_db
def test_keys_used_in_algorithm_session_js(client):
    """All of these values are used in algorithms/js/session.js"""
    u = UserFactory()
    j = AlgorithmJobFactory(creator=u)
    s = RawImageUploadSessionFactory(creator=u)

    # Session API
    response = get_view_for_user(client=client, url=s.api_url, user=u)
    assert response.status_code == 200
    assert response.json()["status"] == "Queued"
    assert response.json()["api_url"] == s.api_url
    assert response.json()["image_set"] == []

    # Evaluation API
    response = get_view_for_user(client=client, url=j.api_url, user=u)
    assert response.status_code == 200
    assert response.json()["status"] == "Queued"
    assert response.json()["api_url"] == j.api_url

    # Job API
    response = get_view_for_user(
        client=client,
        viewname="api:algorithms-job-list",
        user=u,
        data={"input_image": str(j.inputs.first().image.pk)},
    )
    assert response.status_code == 200
    assert len(response.json()["results"]) == 1
    assert response.json()["results"][0]["pk"] == str(j.pk)


@pytest.mark.django_db
def test_inputs_are_serialized(client):
    u = UserFactory()
    j = AlgorithmJobFactory(creator=u)

    response = get_view_for_user(client=client, url=j.api_url, user=u)
    assert response.json()["inputs"][0]["image"] == str(
        j.inputs.first().image.api_url.replace("https://", "http://")
    )
