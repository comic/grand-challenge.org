import pytest

from grandchallenge.datasets.models import ImageSet
from tests.factories import ChallengeFactory


@pytest.mark.django_db
def test_imageset_creation():
    initial_count = 2  # Automatically created
    assert ImageSet.objects.all().count() == initial_count

    challenge = ChallengeFactory()

    assert ImageSet.objects.all().count() == 2 + initial_count
    assert len(challenge.imageset_set.all()) == 2
    assert len(challenge.imageset_set.filter(phase=ImageSet.TRAINING)) == 1
    assert len(challenge.imageset_set.filter(phase=ImageSet.TESTING)) == 1
