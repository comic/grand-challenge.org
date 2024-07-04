import pytest
from guardian.shortcuts import assign_perm

from grandchallenge.algorithms.models import Job
from grandchallenge.algorithms.serializers import (
    AlgorithmImageSerializer,
    AlgorithmModelSerializer,
)
from grandchallenge.components.models import InterfaceKind
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
)
from tests.components_tests.factories import ComponentInterfaceFactory
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
        (1),
        (3),
    ),
)
def test_job_list_view_num_queries(
    client, django_assert_num_queries, num_jobs
):
    user = UserFactory()
    AlgorithmJobFactory.create_batch(num_jobs, creator=user)

    with django_assert_num_queries(33) as _:
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


@pytest.mark.django_db
def test_algorithm_image_download_url(
    client, django_capture_on_commit_callbacks, algorithm_io_image, rf
):
    user1, user2 = UserFactory.create_batch(2)
    with django_capture_on_commit_callbacks():
        ai = AlgorithmImageFactory(image__from_path=algorithm_io_image)
    assign_perm("algorithms.download_algorithmimage", user1, ai)

    serialized_ai = AlgorithmImageSerializer(
        ai, context={"request": rf.get("/foo", secure=True)}
    ).data

    resp = get_view_for_user(
        url=serialized_ai["image"], client=client, user=user2
    )
    assert resp.status_code == 403

    resp = get_view_for_user(
        url=serialized_ai["image"], client=client, user=user1
    )
    assert resp.status_code == 302
    assert (
        f"grand-challenge-protected/docker/images/algorithms/algorithmimage/{ai.pk}/algorithm-io-latest.tar"
        in str(resp.url)
    )


@pytest.mark.django_db
def test_algorithm_model_download_url(
    client, django_capture_on_commit_callbacks, algorithm_io_image, rf
):
    user1, user2 = UserFactory.create_batch(2)
    with django_capture_on_commit_callbacks():
        model = AlgorithmModelFactory(model__from_path=algorithm_io_image)
    assign_perm("algorithms.download_algorithmmodel", user1, model)

    serialized_model = AlgorithmModelSerializer(
        model, context={"request": rf.get("/foo", secure=True)}
    ).data

    resp = get_view_for_user(
        url=serialized_model["model"], client=client, user=user2
    )
    assert resp.status_code == 403

    resp = get_view_for_user(
        url=serialized_model["model"], client=client, user=user1
    )
    assert resp.status_code == 302
    assert (
        f"grand-challenge-protected/models/algorithms/algorithmmodel/{model.pk}/algorithm-io-latest.tar"
        in str(resp.url)
    )
