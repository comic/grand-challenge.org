# -*- coding: utf-8 -*-
import pytest

from grandchallenge.datasets.models import ImageSet
from tests.factories import ImageSetFactory, ImageFileFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize("phase", [ImageSet.TRAINING, ImageSet.TESTING])
def test_imageset_image_download(client, TwoChallengeSets, phase):
    """
    Only participants of a challenge should be able to download imageset images
    """

    imageset = ImageSetFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge, phase=phase
    )

    image_file = ImageFileFactory()

    imageset.images.add(image_file.image)

    tests = [
        (404, None),
        (404, TwoChallengeSets.ChallengeSet1.non_participant),
        (200, TwoChallengeSets.ChallengeSet1.participant),
        (200, TwoChallengeSets.ChallengeSet1.participant1),
        (200, TwoChallengeSets.ChallengeSet1.creator),
        (200, TwoChallengeSets.ChallengeSet1.admin),
        (404, TwoChallengeSets.ChallengeSet2.non_participant),
        (404, TwoChallengeSets.ChallengeSet2.participant),
        (404, TwoChallengeSets.ChallengeSet2.participant1),
        (404, TwoChallengeSets.ChallengeSet2.creator),
        (404, TwoChallengeSets.ChallengeSet2.admin),
        (200, TwoChallengeSets.admin12),
        (200, TwoChallengeSets.participant12),
        (200, TwoChallengeSets.admin1participant2),
    ]

    for test in tests:
        response = get_view_for_user(
            url=image_file.file.url, client=client, user=test[1]
        )
        assert response.status_code == test[0]
