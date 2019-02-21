import pytest
from django.conf import settings
from rest_framework.authtoken.models import Token

from grandchallenge.datasets.models import ImageSet, AnnotationSet
from tests.factories import (
    ImageFileFactory,
    AnnotationSetFactory,
    UserFactory,
    SubmissionFactory,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind", [AnnotationSet.PREDICTION, AnnotationSet.GROUNDTRUTH]
)
@pytest.mark.parametrize("phase", [ImageSet.TRAINING, ImageSet.TESTING])
def test_imageset_annotationset_download(
    client, TwoChallengeSets, phase, kind
):
    """
    Only participants of a challenge should be able to download imageset images
    """

    imageset = TwoChallengeSets.ChallengeSet1.challenge.imageset_set.get(
        phase=phase
    )
    image_file = ImageFileFactory()
    imageset.images.add(image_file.image)

    annotationset = AnnotationSetFactory(base=imageset, kind=kind)
    annotation_file = ImageFileFactory()
    annotationset.images.add(annotation_file.image)

    staff_user = UserFactory(is_staff=True)
    staff_token = Token.objects.create(user=staff_user)

    tests = [
        # (
        #   image response + annotation response not test ground truth,
        #   annotation response - testing gt,
        #   user
        # )
        (404, 404, None),
        (200, 200, staff_user),
        (404, 404, TwoChallengeSets.ChallengeSet1.non_participant),
        (200, 404, TwoChallengeSets.ChallengeSet1.participant),
        (200, 404, TwoChallengeSets.ChallengeSet1.participant1),
        (200, 200, TwoChallengeSets.ChallengeSet1.creator),
        (200, 200, TwoChallengeSets.ChallengeSet1.admin),
        (404, 404, TwoChallengeSets.ChallengeSet2.non_participant),
        (404, 404, TwoChallengeSets.ChallengeSet2.participant),
        (404, 404, TwoChallengeSets.ChallengeSet2.participant1),
        (404, 404, TwoChallengeSets.ChallengeSet2.creator),
        (404, 404, TwoChallengeSets.ChallengeSet2.admin),
        (200, 200, TwoChallengeSets.admin12),
        (200, 404, TwoChallengeSets.participant12),
        (200, 200, TwoChallengeSets.admin1participant2),
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

    # Someone with a staff token should be able to get all images
    response = client.get(
        image_file.file.url, HTTP_AUTHORIZATION=f"Token {staff_token.key}"
    )
    assert response.status_code == 200

    response = client.get(
        annotation_file.file.url, HTTP_AUTHORIZATION=f"Token {staff_token.key}"
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_image_response(client):
    image_file = ImageFileFactory()

    response = get_view_for_user(
        url=image_file.file.url, client=client, user=None
    )

    # Forbidden view
    assert response.status_code == 404
    assert not response.has_header("x-accel-redirect")

    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        url=image_file.file.url, client=client, user=staff_user
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
def test_submission_download(client, TwoChallengeSets):
    """
    Only the challenge admin should be able to download submissions
    """
    submission = SubmissionFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        creator=TwoChallengeSets.ChallengeSet1.participant,
    )

    tests = [
        # (
        #   image response + annotation response not test ground truth,
        #   user
        # )
        (404, None),
        (404, TwoChallengeSets.ChallengeSet1.non_participant),
        (404, TwoChallengeSets.ChallengeSet1.participant),
        (404, TwoChallengeSets.ChallengeSet1.participant1),
        (200, TwoChallengeSets.ChallengeSet1.creator),
        (200, TwoChallengeSets.ChallengeSet1.admin),
        (404, TwoChallengeSets.ChallengeSet2.non_participant),
        (404, TwoChallengeSets.ChallengeSet2.participant),
        (404, TwoChallengeSets.ChallengeSet2.participant1),
        (404, TwoChallengeSets.ChallengeSet2.creator),
        (404, TwoChallengeSets.ChallengeSet2.admin),
        (200, TwoChallengeSets.admin12),
        (404, TwoChallengeSets.participant12),
        (200, TwoChallengeSets.admin1participant2),
    ]

    for test in tests:
        response = get_view_for_user(
            url=submission.file.url, client=client, user=test[1]
        )
        assert response.status_code == test[0]
