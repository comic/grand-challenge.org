import pytest
from django.core import mail

from grandchallenge.subdomains.utils import reverse
from grandchallenge.participants.models import RegistrationRequest
from tests.factories import UserFactory, RegistrationRequestFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize("participant_review", [True, False])
def test_new_registration_email(participant_review, client, ChallengeSet):
    user = UserFactory()
    ChallengeSet.challenge.require_participant_review = participant_review
    ChallengeSet.challenge.save()
    assert not RegistrationRequest.objects.filter(
        user=user, challenge=ChallengeSet.challenge
    ).exists()
    response = get_view_for_user(
        viewname="participants:registration-create",
        client=client,
        method=client.post,
        user=user,
        challenge=ChallengeSet.challenge,
    )
    assert response.status_code == 302
    assert RegistrationRequest.objects.filter(
        user=user, challenge=ChallengeSet.challenge
    ).exists()
    if participant_review:
        email = mail.outbox[-1]
        approval_link = reverse(
            "participants:registration-list",
            kwargs={"challenge_short_name": ChallengeSet.challenge.short_name},
        )
        assert ChallengeSet.admin.email in email.to
        assert "new participation request" in email.subject.lower()
        assert ChallengeSet.challenge.short_name in email.subject
        assert approval_link in email.alternatives[0][0]
    else:
        with pytest.raises(IndexError):
            # No emails if no review
            # noinspection PyStatementEffect
            mail.outbox[-1]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "new_state", [RegistrationRequest.REJECTED, RegistrationRequest.ACCEPTED]
)
def test_registration_updated_email(new_state, client, ChallengeSet):
    rr = RegistrationRequestFactory(challenge=ChallengeSet.challenge)
    response = get_view_for_user(
        viewname="participants:registration-update",
        client=client,
        method=client.post,
        user=ChallengeSet.admin,
        challenge=ChallengeSet.challenge,
        reverse_kwargs={"pk": rr.pk},
        data={"status": new_state},
    )
    assert response.status_code == 302
    email = mail.outbox[-1]
    assert rr.user.email in email.to
    if new_state == RegistrationRequest.ACCEPTED:
        assert "request accepted" in email.subject.lower()
    else:
        assert "request rejected" in email.subject.lower()
    assert ChallengeSet.challenge.short_name in email.body
