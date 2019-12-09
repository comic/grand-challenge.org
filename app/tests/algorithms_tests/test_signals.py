from unittest import mock

import pytest

from grandchallenge.algorithms.models import AlgorithmPermissionRequest
from tests.algorithms_tests.factories import (
    AlgorithmPermissionRequestFactory,
    AlgorithmResultFactory,
)
from tests.algorithms_tests.utils import TwoAlgorithms
from tests.factories import ImageFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_user_can_download_images(client, reverse):
    alg_set = TwoAlgorithms()

    j1_creator, j2_creator = UserFactory(), UserFactory()

    alg1_result = AlgorithmResultFactory(
        job__algorithm_image__algorithm=alg_set.alg1, job__creator=j1_creator
    )
    alg2_result = AlgorithmResultFactory(
        job__algorithm_image__algorithm=alg_set.alg2, job__creator=j2_creator
    )

    im1, im2, im3, im4 = (
        ImageFactory(),
        ImageFactory(),
        ImageFactory(),
        ImageFactory(),
    )

    if reverse:
        for im in [im1, im2, im3, im4]:
            im.algorithm_results.add(alg1_result, alg2_result)
        for im in [im3, im4]:
            im.algorithm_results.remove(alg1_result, alg2_result)
        for im in [im1, im2]:
            im.algorithm_results.remove(alg2_result)
    else:
        # Test that adding images works
        alg1_result.images.add(im1, im2, im3, im4)
        # Test that removing images works
        alg1_result.images.remove(im3, im4)

    tests = (
        (None, 401, []),
        (alg_set.creator, 200, []),
        (alg_set.editor1, 200, [alg1_result.job.image.pk, im1.pk, im2.pk]),
        (alg_set.user1, 200, []),
        (j1_creator, 200, [alg1_result.job.image.pk, im1.pk, im2.pk]),
        (alg_set.editor2, 200, [alg2_result.job.image.pk]),
        (alg_set.user2, 200, []),
        (j2_creator, 200, [alg2_result.job.image.pk]),
        (alg_set.u, 200, []),
    )

    for test in tests:
        response = get_view_for_user(
            viewname="api:image-list",
            client=client,
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]

        if test[1] != 401:
            # We provided auth details and get a response
            assert response.json()["count"] == len(test[2])

            pks = [obj["pk"] for obj in response.json()["results"]]

            for pk in test[2]:
                assert str(pk) in pks

    # Test clearing
    if reverse:
        im1.algorithm_results.clear()
        im2.algorithm_results.clear()
    else:
        alg1_result.images.clear()

    response = get_view_for_user(
        viewname="api:image-list",
        client=client,
        user=j1_creator,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1


@pytest.mark.django_db
def test_process_algorithm_permission_request():
    # signals.pre_save.connect(process_algorithm_permission_request, sender=AlgorithmPermissionRequest, weak=False)
    with mock.patch(
        "grandchallenge.algorithms.signals.send_permission_request_email"
    ) as send_email:
        pr = AlgorithmPermissionRequestFactory()
        assert pr.status == AlgorithmPermissionRequest.PENDING
        send_email.assert_called_once
        assert not pr.algorithm.is_user(pr.user)

    with mock.patch(
        "grandchallenge.algorithms.signals.send_permission_denied_email"
    ) as send_email:
        pr.status = AlgorithmPermissionRequest.REJECTED
        pr.save()
        send_email.assert_called_once()
        assert not pr.algorithm.is_user(pr.user)

    with mock.patch(
        "grandchallenge.algorithms.signals.send_permission_granted_email"
    ) as send_email:
        pr.status = AlgorithmPermissionRequest.ACCEPTED
        pr.save()
        send_email.assert_called_once()
        assert pr.algorithm.is_user(pr.user)
