import pytest

from grandchallenge.algorithms.models import Job
from grandchallenge.components.models import InterfaceKind
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_job_detail(client):
    user = UserFactory()
    job = AlgorithmJobFactory(creator=user, time_limit=60)
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
    j = AlgorithmJobFactory(creator=u, time_limit=60)

    response = get_view_for_user(client=client, url=j.api_url, user=u)
    assert response.json()["inputs"][0]["image"] == str(
        j.inputs.first().image.api_url.replace("https://", "http://")
    )


@pytest.mark.django_db
def test_job_time_limit(client):
    algorithm = AlgorithmFactory(time_limit=600)
    algorithm_image = AlgorithmImageFactory(
        algorithm=algorithm,
        is_desired_version=True,
        is_manifest_valid=True,
        is_in_registry=True,
    )

    user = UserFactory()
    algorithm.add_editor(user=user)

    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.ANY, store_in_database=True
    )
    algorithm.inputs.set([ci])

    response = get_view_for_user(
        viewname="api:algorithms-job-list",
        client=client,
        method=client.post,
        user=user,
        follow=True,
        content_type="application/json",
        data={
            "algorithm": algorithm.api_url,
            "inputs": [{"interface": ci.slug, "value": '{"Foo": "bar"}'}],
        },
    )

    assert response.status_code == 201

    job = Job.objects.get()

    assert job.algorithm_image == algorithm_image
    assert job.time_limit == 600


@pytest.mark.django_db
@pytest.mark.parametrize(
    "num_jobs",
    (
        1,
        3,
    ),
)
def test_job_list_view_num_queries(
    client, num_jobs, django_assert_max_num_queries
):
    user = UserFactory()
    AlgorithmJobFactory.create_batch(num_jobs, creator=user, time_limit=60)

    with django_assert_max_num_queries(32) as _:
        response = get_view_for_user(
            viewname="api:algorithms-job-list",
            client=client,
            method=client.get,
            user=user,
            content_type="application/json",
        )

        # Sanity checks
        assert response.status_code == 200
        assert len(response.json()["results"]) == num_jobs
