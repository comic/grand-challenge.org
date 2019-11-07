import pytest
from django.conf import settings
from guardian.shortcuts import assign_perm

from grandchallenge.datasets.models import AnnotationSet, ImageSet
from tests.factories import (
    AnnotationSetFactory,
    ImageFileFactory,
    SubmissionFactory,
    UserFactory,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind", [AnnotationSet.PREDICTION, AnnotationSet.GROUNDTRUTH]
)
@pytest.mark.parametrize("phase", [ImageSet.TRAINING, ImageSet.TESTING])
def test_imageset_annotationset_download(
    client, two_challenge_sets, phase, kind
):
    """Only participants of a challenge should be able to download imageset images."""

    imageset = two_challenge_sets.challenge_set_1.challenge.imageset_set.get(
        phase=phase
    )
    image_file = ImageFileFactory()
    imageset.images.add(image_file.image)

    annotationset = AnnotationSetFactory(base=imageset, kind=kind)
    annotation_file = ImageFileFactory()
    annotationset.images.add(annotation_file.image)

    tests = [
        # (
        #   image response + annotation response not test ground truth,
        #   annotation response - testing gt,
        #   user
        # )
        (404, 404, None),
        (404, 404, UserFactory()),
        (404, 404, UserFactory(is_staff=True)),
        (404, 404, two_challenge_sets.challenge_set_1.non_participant),
        (200, 404, two_challenge_sets.challenge_set_1.participant),
        (200, 404, two_challenge_sets.challenge_set_1.participant1),
        (200, 200, two_challenge_sets.challenge_set_1.creator),
        (200, 200, two_challenge_sets.challenge_set_1.admin),
        (404, 404, two_challenge_sets.challenge_set_2.non_participant),
        (404, 404, two_challenge_sets.challenge_set_2.participant),
        (404, 404, two_challenge_sets.challenge_set_2.participant1),
        (404, 404, two_challenge_sets.challenge_set_2.creator),
        (404, 404, two_challenge_sets.challenge_set_2.admin),
        (200, 200, two_challenge_sets.admin12),
        (200, 404, two_challenge_sets.participant12),
        (200, 200, two_challenge_sets.admin1participant2),
    ]

    for test in tests:

        response = get_view_for_user(
            url=image_file.file.url, client=client, user=test[2]
        )
        assert response.status_code == test[0]

        response = get_view_for_user(
            url=annotation_file.file.url, client=client, user=test[2]
        )
        if phase == ImageSet.TESTING and kind == AnnotationSet.GROUNDTRUTH:
            # testing ground truth
            assert response.status_code == test[1]
        else:
            # training ground truth, training predictions and
            # ground truth predictions
            assert response.status_code == test[0]


@pytest.mark.django_db
def test_image_response(client):
    image_file = ImageFileFactory()
    user = UserFactory()

    response = get_view_for_user(
        url=image_file.file.url, client=client, user=user
    )

    # Forbidden view
    assert response.status_code == 404
    assert not response.has_header("x-accel-redirect")

    assign_perm("view_image", user, image_file.image)

    response = get_view_for_user(
        url=image_file.file.url, client=client, user=user
    )

    assert response.status_code == 200
    assert response.has_header("x-accel-redirect")

    redirect = response.get("x-accel-redirect")

    assert redirect.startswith(
        f"/{settings.PROTECTED_S3_STORAGE_KWARGS['bucket_name']}/"
    )
    assert "AWSAccessKeyId" in redirect
    assert "Signature" in redirect
    assert "Expires" in redirect


@pytest.mark.django_db
def test_submission_download(client, two_challenge_sets):
    """Only the challenge admin should be able to download submissions."""
    submission = SubmissionFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        creator=two_challenge_sets.challenge_set_1.participant,
    )

    tests = [
        # (
        #   image response + annotation response not test ground truth,
        #   user
        # )
        (404, None),
        (404, two_challenge_sets.challenge_set_1.non_participant),
        (404, two_challenge_sets.challenge_set_1.participant),
        (404, two_challenge_sets.challenge_set_1.participant1),
        (200, two_challenge_sets.challenge_set_1.creator),
        (200, two_challenge_sets.challenge_set_1.admin),
        (404, two_challenge_sets.challenge_set_2.non_participant),
        (404, two_challenge_sets.challenge_set_2.participant),
        (404, two_challenge_sets.challenge_set_2.participant1),
        (404, two_challenge_sets.challenge_set_2.creator),
        (404, two_challenge_sets.challenge_set_2.admin),
        (200, two_challenge_sets.admin12),
        (404, two_challenge_sets.participant12),
        (200, two_challenge_sets.admin1participant2),
    ]

    for test in tests:
        response = get_view_for_user(
            url=submission.file.url, client=client, user=test[1]
        )
        assert response.status_code == test[0]
