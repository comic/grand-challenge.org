import pytest
from django.core import mail

from grandchallenge.participants.models import RegistrationRequest
from grandchallenge.subdomains.utils import reverse
from tests.factories import RegistrationRequestFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize("participant_review", [True, False])
def test_new_registration_email(participant_review, client, challenge_set):
    user = UserFactory()

    challenge_set.challenge.require_participant_review = participant_review
    challenge_set.challenge.save()

    assert not RegistrationRequest.objects.filter(
        user=user, challenge=challenge_set.challenge
    ).exists()

    response = get_view_for_user(
        viewname="participants:registration-create",
        client=client,
        method=client.post,
        user=user,
        challenge=challenge_set.challenge,
    )

    assert response.status_code == 302
    assert RegistrationRequest.objects.filter(
        user=user, challenge=challenge_set.challenge
    ).exists()

    if participant_review:
        approval_link = reverse(
            "participants:registration-list",
            kwargs={
                "challenge_short_name": challenge_set.challenge.short_name
            },
        )

        admin_emails = [
            e for e in mail.outbox if challenge_set.admin.email in e.to
        ]
        assert len(admin_emails) == 1
        email = admin_emails[0]

        assert challenge_set.admin.email in email.to
        assert "new participation request" in email.subject.lower()
        assert challenge_set.challenge.short_name in email.subject
        assert approval_link in email.alternatives[0][0]
    else:
        # No emails if no review
        assert len(mail.outbox) == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "new_state", [RegistrationRequest.REJECTED, RegistrationRequest.ACCEPTED]
)
def test_registration_updated_email(new_state, client, challenge_set):
    rr = RegistrationRequestFactory(challenge=challenge_set.challenge)
    response = get_view_for_user(
        viewname="participants:registration-update",
        client=client,
        method=client.post,
        user=challenge_set.admin,
        challenge=challenge_set.challenge,
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
    assert challenge_set.challenge.short_name in email.body
