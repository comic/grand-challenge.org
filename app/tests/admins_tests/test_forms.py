import pytest
from django.core import mail

from grandchallenge.admins.forms import AdminsForm
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_admins_add(client, TwoChallengeSets):
    user = UserFactory()
    assert not TwoChallengeSets.ChallengeSet1.challenge.is_admin(user=user)
    assert not TwoChallengeSets.ChallengeSet2.challenge.is_admin(user=user)
    response = get_view_for_user(
        viewname="admins:update",
        client=client,
        method=client.post,
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        data={"user": user.pk, "action": AdminsForm.ADD},
        user=TwoChallengeSets.ChallengeSet1.admin,
    )
    assert response.status_code == 302
    email = mail.outbox[-1]
    assert TwoChallengeSets.ChallengeSet1.challenge.short_name in email.subject
    assert user.email in email.to
    assert TwoChallengeSets.ChallengeSet1.challenge.is_admin(user=user)
    assert not TwoChallengeSets.ChallengeSet2.challenge.is_admin(user=user)


@pytest.mark.django_db
def test_admins_remove(client, TwoChallengeSets):
    assert TwoChallengeSets.ChallengeSet1.challenge.is_admin(
        user=TwoChallengeSets.admin12
    )
    assert TwoChallengeSets.ChallengeSet2.challenge.is_admin(
        user=TwoChallengeSets.admin12
    )
    response = get_view_for_user(
        viewname="admins:update",
        client=client,
        method=client.post,
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        data={
            "user": TwoChallengeSets.admin12.pk,
            "action": AdminsForm.REMOVE,
        },
        user=TwoChallengeSets.ChallengeSet1.admin,
    )
    assert response.status_code == 302
    assert not TwoChallengeSets.ChallengeSet1.challenge.is_admin(
        user=TwoChallengeSets.admin12
    )
    assert TwoChallengeSets.ChallengeSet2.challenge.is_admin(
        user=TwoChallengeSets.admin12
    )
