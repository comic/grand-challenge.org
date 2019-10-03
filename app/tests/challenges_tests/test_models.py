import pytest
from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.challenges.models import Challenge
from tests.factories import ChallengeFactory


@pytest.mark.django_db
def test_group_deletion():
    challenge = ChallengeFactory()
    participants_group = challenge.participants_group
    admins_group = challenge.admins_group

    assert participants_group
    assert admins_group

    Challenge.objects.filter(pk__in=[challenge.pk]).delete()

    with pytest.raises(ObjectDoesNotExist):
        participants_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        admins_group.refresh_from_db()


@pytest.mark.django_db
@pytest.mark.parametrize("group", ["participants_group", "admins_group"])
def test_group_deletion_reverse(group):
    challenge = ChallengeFactory()
    participants_group = challenge.participants_group
    admins_group = challenge.admins_group

    assert participants_group
    assert admins_group

    getattr(challenge, group).delete()

    with pytest.raises(ObjectDoesNotExist):
        participants_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        admins_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        challenge.refresh_from_db()
