import pytest

from grandchallenge.participants.models import RegistrationRequest
from tests.factories import RegistrationRequestFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_registration_no_review_workflow(challenge_set):
    user = UserFactory()
    challenge_set.challenge.require_participant_review = False
    challenge_set.challenge.save()
    RegistrationRequestFactory(challenge=challenge_set.challenge, user=user)
    assert challenge_set.challenge.is_participant(user)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "choice,expected",
    [
        (RegistrationRequest.ACCEPTED, True),
        (RegistrationRequest.REJECTED, False),
        (RegistrationRequest.PENDING, False),
    ],
)
def test_registration_review_workflow(choice, expected, client, challenge_set):
    user = UserFactory()
    challenge_set.challenge.require_participant_review = True
    challenge_set.challenge.save()
    rr = RegistrationRequestFactory(
        challenge=challenge_set.challenge, user=user
    )
    assert not challenge_set.challenge.is_participant(user)
    assert rr.status == RegistrationRequest.PENDING
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="participants:registration-update",
        challenge=challenge_set.challenge,
        user=challenge_set.admin,
        reverse_kwargs={"pk": rr.pk},
        data={"status": choice},
    )
    assert response.status_code == 302
    assert challenge_set.challenge.is_participant(user) == expected
    assert RegistrationRequest.objects.get(pk=rr.pk).status == choice


@pytest.mark.django_db
def test_registration_admin_changed_mind(client, challenge_set):
    user = UserFactory()
    challenge_set.challenge.require_participant_review = False
    challenge_set.challenge.save()
    rr = RegistrationRequestFactory(
        challenge=challenge_set.challenge, user=user
    )
    assert challenge_set.challenge.is_participant(user)
    assert rr.status == RegistrationRequest.ACCEPTED
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="participants:registration-update",
        challenge=challenge_set.challenge,
        user=challenge_set.admin,
        reverse_kwargs={"pk": rr.pk},
        data={"status": RegistrationRequest.REJECTED},
    )
    assert response.status_code == 302
    assert not challenge_set.challenge.is_participant(user)
    assert (
        RegistrationRequest.objects.get(pk=rr.pk).status
        == RegistrationRequest.REJECTED
    )
