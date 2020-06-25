from unittest import mock

import pytest

from grandchallenge.algorithms.models import AlgorithmPermissionRequest
from tests.algorithms_tests.factories import (
    AlgorithmJobFactory,
    AlgorithmPermissionRequestFactory,
)
from tests.algorithms_tests.utils import TwoAlgorithms
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.factories import ImageFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_user_can_download_images(client, reverse):
    alg_set = TwoAlgorithms()

    j1_creator, j2_creator = UserFactory(), UserFactory()

    alg1_job = AlgorithmJobFactory(
        algorithm_image__algorithm=alg_set.alg1, creator=j1_creator
    )
    alg2_job = AlgorithmJobFactory(
        algorithm_image__algorithm=alg_set.alg2, creator=j2_creator
    )

    iv1, iv2, iv3, iv4 = (
        ComponentInterfaceValueFactory(image=ImageFactory()),
        ComponentInterfaceValueFactory(image=ImageFactory()),
        ComponentInterfaceValueFactory(image=ImageFactory()),
        ComponentInterfaceValueFactory(image=ImageFactory()),
    )

    if reverse:
        for im in [iv1, iv2, iv3, iv4]:
            im.algorithms_jobs_as_output.add(alg1_job, alg2_job)
        for im in [iv3, iv4]:
            im.algorithms_jobs_as_output.remove(alg1_job, alg2_job)
        for im in [iv1, iv2]:
            im.algorithms_jobs_as_output.remove(alg2_job)
    else:
        # Test that adding images works
        alg1_job.outputs.add(iv1, iv2, iv3, iv4)
        # Test that removing images works
        alg1_job.outputs.remove(iv3, iv4)

    tests = (
        (None, 401, []),
        (alg_set.creator, 200, []),
        (
            alg_set.editor1,
            200,
            [
                *[i.image.pk for i in alg1_job.inputs.all()],
                iv1.image.pk,
                iv2.image.pk,
            ],
        ),
        (alg_set.user1, 200, []),
        (
            j1_creator,
            200,
            [
                *[i.image.pk for i in alg1_job.inputs.all()],
                iv1.image.pk,
                iv2.image.pk,
            ],
        ),
        (alg_set.editor2, 200, [i.image.pk for i in alg2_job.inputs.all()],),
        (alg_set.user2, 200, []),
        (j2_creator, 200, [i.image.pk for i in alg2_job.inputs.all()]),
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
        iv1.algorithms_jobs_as_output.clear()
        iv2.algorithms_jobs_as_output.clear()
    else:
        alg1_job.outputs.clear()

    response = get_view_for_user(
        viewname="api:image-list",
        client=client,
        user=j1_creator,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_user_can_download_input_images(client, reverse):
    alg_set = TwoAlgorithms()

    j1_creator, j2_creator = UserFactory(), UserFactory()

    alg1_job = AlgorithmJobFactory(
        algorithm_image__algorithm=alg_set.alg1, creator=j1_creator
    )
    alg2_job = AlgorithmJobFactory(
        algorithm_image__algorithm=alg_set.alg2, creator=j2_creator
    )

    iv1, iv2, iv3, iv4 = (
        ComponentInterfaceValueFactory(image=ImageFactory()),
        ComponentInterfaceValueFactory(image=ImageFactory()),
        ComponentInterfaceValueFactory(image=ImageFactory()),
        ComponentInterfaceValueFactory(image=ImageFactory()),
    )

    alg1_origin_input = [i.image.pk for i in alg1_job.inputs.all()]
    alg2_origin_input = [i.image.pk for i in alg2_job.inputs.all()]

    if reverse:
        for iv in [iv1, iv2, iv3, iv4]:
            iv.algorithms_jobs_as_input.add(alg1_job, alg2_job)
        for iv in [iv3, iv4]:
            iv.algorithms_jobs_as_input.remove(alg1_job, alg2_job)
        for iv in [iv1, iv2]:
            iv.algorithms_jobs_as_input.remove(alg2_job)
    else:
        # Test that adding images works
        alg1_job.inputs.add(iv1, iv2, iv3, iv4)
        # Test that removing images works
        alg1_job.inputs.remove(iv3, iv4)

    tests = (
        (None, 401, []),
        (alg_set.creator, 200, []),
        (
            alg_set.editor1,
            200,
            [*alg1_origin_input, iv1.image.pk, iv2.image.pk],
        ),
        (alg_set.user1, 200, []),
        (j1_creator, 200, [*alg1_origin_input, iv1.image.pk, iv2.image.pk],),
        (alg_set.editor2, 200, alg2_origin_input),
        (alg_set.user2, 200, []),
        (j2_creator, 200, alg2_origin_input),
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
        iv1.algorithms_jobs_as_input.clear()
        iv2.algorithms_jobs_as_input.clear()
    else:
        alg1_job.inputs.clear()

    response = get_view_for_user(
        viewname="api:image-list",
        client=client,
        user=j1_creator,
        content_type="application/json",
    )
    assert response.status_code == 200

    if reverse:
        assert response.json()["count"] == 1
    else:
        assert response.json()["count"] == 0


@pytest.mark.django_db
def test_process_algorithm_permission_request():
    # signals.pre_save.connect(process_algorithm_permission_request, sender=AlgorithmPermissionRequest, weak=False)
    with mock.patch(
        "grandchallenge.core.signals.send_permission_request_email"
    ) as send_email:
        pr = AlgorithmPermissionRequestFactory()
        assert pr.status == AlgorithmPermissionRequest.PENDING
        send_email.assert_called_once
        assert not pr.algorithm.is_user(pr.user)

    with mock.patch(
        "grandchallenge.core.signals.send_permission_denied_email"
    ) as send_email:
        pr.status = AlgorithmPermissionRequest.REJECTED
        pr.save()
        send_email.assert_called_once()
        assert not pr.algorithm.is_user(pr.user)

    with mock.patch(
        "grandchallenge.core.signals.send_permission_granted_email"
    ) as send_email:
        pr.status = AlgorithmPermissionRequest.ACCEPTED
        pr.save()
        send_email.assert_called_once()
        assert pr.algorithm.is_user(pr.user)
