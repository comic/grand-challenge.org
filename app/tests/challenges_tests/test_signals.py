import pytest

from grandchallenge.datasets.models import ImageSet
from tests.factories import ChallengeFactory


@pytest.mark.django_db
def test_imageset_creation():
    assert ImageSet.objects.all().count() == 0

    challenge = ChallengeFactory()

    assert ImageSet.objects.all().count() == 2
    assert len(challenge.imageset_set.all()) == 2
    assert len(challenge.imageset_set.filter(phase=ImageSet.TRAINING)) == 1
    assert len(challenge.imageset_set.filter(phase=ImageSet.TESTING)) == 1
