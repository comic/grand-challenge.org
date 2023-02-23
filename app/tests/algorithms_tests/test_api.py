import pytest

from tests.algorithms_tests.factories import AlgorithmJobFactory
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
def test_inputs_are_serialized(client):
    u = UserFactory()
    j = AlgorithmJobFactory(creator=u)

    response = get_view_for_user(client=client, url=j.api_url, user=u)
    assert response.json()["inputs"][0]["image"] == str(
        j.inputs.first().image.api_url.replace("https://", "http://")
    )
