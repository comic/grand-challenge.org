import pytest
from django.core.exceptions import ValidationError

from grandchallenge.datasets.models import ImageSet
from tests.factories import ChallengeFactory


@pytest.mark.django_db
def test_unique_dataset_phase(client):
    challenge = ChallengeFactory()

    with pytest.raises(ValidationError):
        ImageSet.objects.create(challenge=challenge, phase=ImageSet.TRAINING)

    with pytest.raises(ValidationError):
        ImageSet.objects.create(challenge=challenge, phase=ImageSet.TESTING)
