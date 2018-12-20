import pytest

from grandchallenge.participants.models import RegistrationRequest
from tests.factories import RegistrationRequestFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_registration_no_review_workflow(ChallengeSet):
    user = UserFactory()
    ChallengeSet.challenge.require_participant_review = False
    ChallengeSet.challenge.save()
    RegistrationRequestFactory(challenge=ChallengeSet.challenge, user=user)
    assert ChallengeSet.challenge.is_participant(user)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "choice,expected",
    [
        (RegistrationRequest.ACCEPTED, True),
        (RegistrationRequest.REJECTED, False),
        (RegistrationRequest.PENDING, False),
    ],
)
def test_registration_review_workflow(choice, expected, client, ChallengeSet):
    user = UserFactory()
    ChallengeSet.challenge.require_participant_review = True
    ChallengeSet.challenge.save()
    rr = RegistrationRequestFactory(
        challenge=ChallengeSet.challenge, user=user
    )
    assert not ChallengeSet.challenge.is_participant(user)
    assert rr.status == RegistrationRequest.PENDING
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="participants:registration-update",
        challenge=ChallengeSet.challenge,
        user=ChallengeSet.admin,
        reverse_kwargs={"pk": rr.pk},
        data={"status": choice},
    )
    assert response.status_code == 302
    assert ChallengeSet.challenge.is_participant(user) == expected
    assert RegistrationRequest.objects.get(pk=rr.pk).status == choice


@pytest.mark.django_db
def test_registration_admin_changed_mind(client, ChallengeSet):
    user = UserFactory()
    ChallengeSet.challenge.require_participant_review = False
    ChallengeSet.challenge.save()
    rr = RegistrationRequestFactory(
        challenge=ChallengeSet.challenge, user=user
    )
    assert ChallengeSet.challenge.is_participant(user)
    assert rr.status == RegistrationRequest.ACCEPTED
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="participants:registration-update",
        challenge=ChallengeSet.challenge,
        user=ChallengeSet.admin,
        reverse_kwargs={"pk": rr.pk},
        data={"status": RegistrationRequest.REJECTED},
    )
    assert response.status_code == 302
    assert not ChallengeSet.challenge.is_participant(user)
    assert (
        RegistrationRequest.objects.get(pk=rr.pk).status
        == RegistrationRequest.REJECTED
    )
