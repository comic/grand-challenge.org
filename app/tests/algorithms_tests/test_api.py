import pytest

from grandchallenge.algorithms.models import Job

from tests.utils import get_view_for_user
from tests.factories import UserFactory
from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    AlgorithmJobFactory,
    AlgorithmResultFactory,
    ImageFactory,
)


@pytest.mark.django_db
def test_algorithm_image_list(client):
    user = UserFactory(is_staff=True)
    algoi1, algoi2 = AlgorithmImageFactory(), AlgorithmImageFactory()
    job1, job2 = (
        AlgorithmJobFactory(algorithm_image=algoi1),
        AlgorithmJobFactory(algorithm_image=algoi2),
    )
    result1, result2 = (
        AlgorithmResultFactory(job=job1, output={"cancer_score": 0.01}),
        AlgorithmResultFactory(job=job2, output={"cancer_score": 0.5}),
    )
    response = get_view_for_user(
        viewname="api:algorithms-image-list", user=user, client=client
    )
    assert response.status_code == 200
    assert response.json()["count"] == 2

    response = get_view_for_user(
        viewname="api:algorithms-image-detail",
        reverse_kwargs={"pk": algoi1.pk},
        user=user,
        client=client,
    )
    assert response.status_code == 200

    response = get_view_for_user(
        viewname="api:algorithms-job-list", user=user, client=client
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["pk"] == str(job1.pk)
    assert (
        response.json()["results"][0]["algorithm_image"]
        == f"http://testserver/api/v1/algorithms/images/{algoi1.pk}/"
    )
    assert response.json()["results"][1]["pk"] == str(job2.pk)
    assert (
        response.json()["results"][1]["algorithm_image"]
        == f"http://testserver/api/v1/algorithms/images/{algoi2.pk}/"
    )

    response = get_view_for_user(
        viewname="api:algorithms-result-list", user=user, client=client
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["pk"] == str(result1.pk)
    assert (
        response.json()["results"][0]["job"]
        == f"http://testserver/api/v1/algorithms/jobs/{job1.pk}/"
    )
    assert response.json()["results"][0]["output"] == {"cancer_score": 0.01}
    assert response.json()["results"][1]["pk"] == str(result2.pk)
    assert (
        response.json()["results"][1]["job"]
        == f"http://testserver/api/v1/algorithms/jobs/{job2.pk}/"
    )
    assert response.json()["results"][1]["output"] == {"cancer_score": 0.5}


@pytest.mark.django_db
def test_algorithm_api_permissions(client):
    tests = [(UserFactory(), 403), (UserFactory(is_staff=True), 200)]
    algorithm_image = AlgorithmImageFactory()

    for test in tests:
        response = get_view_for_user(
            client=client,
            viewname="api:algorithms-image-list",
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]

        response = get_view_for_user(
            client=client,
            viewname="api:algorithms-image-detail",
            reverse_kwargs={"pk": algorithm_image.pk},
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]


@pytest.mark.django_db
def test_job_api_permissions(client):
    tests = [(UserFactory(), 403), (UserFactory(is_staff=True), 200)]
    job = AlgorithmJobFactory()

    for test in tests:
        response = get_view_for_user(
            client=client,
            viewname="api:algorithms-job-list",
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]

        response = get_view_for_user(
            client=client,
            viewname="api:algorithms-job-detail",
            reverse_kwargs={"pk": job.pk},
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]


@pytest.mark.django_db
def test_result_api_permissions(client):
    tests = [(UserFactory(), 403), (UserFactory(is_staff=True), 200)]
    result = AlgorithmResultFactory()

    for test in tests:
        response = get_view_for_user(
            client=client,
            viewname="api:algorithms-result-list",
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]

        response = get_view_for_user(
            client=client,
            viewname="api:algorithms-result-detail",
            reverse_kwargs={"pk": result.pk},
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]


@pytest.mark.django_db
def test_job_create(client):
    im = ImageFactory()

    algo_i = AlgorithmImageFactory()

    user = UserFactory(is_staff=True)

    response = get_view_for_user(
        viewname="api:algorithms-job-list",
        user=user,
        client=client,
        method=client.post,
        data={"image": im.api_url, "algorithm_image": algo_i.api_url},
        content_type="application/json",
    )
    assert response.status_code == 201

    job = Job.objects.get(pk=response.data.get("pk"))

    assert job.image == im
    assert job.algorithm_image == algo_i


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_staff, expected_response", [(False, 403), (True, 201)]
)
def test_job_post_permissions(client, is_staff, expected_response):
    # Staff users should be able to post a job
    user = UserFactory(is_staff=is_staff)
    im = ImageFactory()
    algo_image = AlgorithmImageFactory()

    response = get_view_for_user(
        viewname="api:algorithms-job-list",
        user=user,
        client=client,
        method=client.post,
        data={"image": im.api_url, "algorithm_image": algo_image.api_url},
        content_type="application/json",
    )
    assert response.status_code == expected_response
