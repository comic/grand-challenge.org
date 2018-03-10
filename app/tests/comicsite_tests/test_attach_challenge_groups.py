import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command

from comicmodels.models import ComicSite
from tests.factories import ChallengeFactory, UserFactory


@pytest.mark.django_db
def test_attach_challenge_groups():
    challenge = ChallengeFactory()

    challenge.admins_group = None
    challenge.participants_group = None
    challenge.save()

    assert challenge.admins_group is None
    assert challenge.participants_group is None

    admins_group = Group.objects.get(name=challenge.admin_group_name())
    participants_group = Group.objects.get(
        name=challenge.participants_group_name())

    call_command('attach_challenge_groups')

    challenge = ComicSite.objects.get(pk=challenge.pk)

    assert challenge.admins_group == admins_group
    assert challenge.participants_group == participants_group

@pytest.mark.django_db
def test_clean_staff(ChallengeSet):
    superuser = UserFactory(is_staff=True, is_superuser=True)

    ChallengeSet.participant.is_staff = True
    ChallengeSet.participant.save()

    assert not ChallengeSet.creator.is_staff
    assert ChallengeSet.participant.is_staff

    call_command('clean_staff')

    assert not User.objects.get(pk=ChallengeSet.creator.pk).is_staff
    assert not User.objects.get(pk=ChallengeSet.participant.pk).is_staff
    assert User.objects.get(pk=superuser.pk).is_staff

