# -*- coding: utf-8 -*-
import pytest

from grandchallenge.datasets.models import ImageSet, AnnotationSet
from tests.factories import (
    ImageSetFactory,
    ImageFileFactory,
    AnnotationSetFactory,
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

    imageset = ImageSetFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge, phase=phase
    )
    image_file = ImageFileFactory()
    imageset.images.add(image_file.image)

    annotationset = AnnotationSetFactory(base=imageset, kind=kind)
    annotation_file = ImageFileFactory()
    annotationset.images.add(annotation_file.image)

    tests = [
        # (image response + annotation response not test ground truth, annoation response - testing gt, user)
        (404, 404, None),
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
            # training ground truth, training predictions and ground truth predictions
            assert response.status_code == test[0]
