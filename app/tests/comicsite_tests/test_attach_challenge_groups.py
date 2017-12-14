import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from comicmodels.models import ComicSite
from tests.factories import ChallengeFactory


@pytest.mark.django_db
def test_attach_challenge_groups():
    challenge = ChallengeFactory()

    assert challenge.admins_group is None
    assert challenge.participants_group is None

    admins_group = Group.objects.get(name=challenge.admin_group_name())
    participants_group = Group.objects.get(
        name=challenge.participants_group_name())

    call_command('attach_challenge_groups')

    challenge = ComicSite.objects.get(pk=challenge.pk)

    assert challenge.admins_group == admins_group
    assert challenge.participants_group == participants_group
