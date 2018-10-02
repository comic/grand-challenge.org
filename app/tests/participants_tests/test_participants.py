import pytest

from grandchallenge.participants.models import RegistrationRequest
from tests.factories import UserFactory, RegistrationRequestFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_registration_request_create_post(client, TwoChallengeSets):
    user = UserFactory()
    assert not RegistrationRequest.objects.filter(
        user=user, challenge=TwoChallengeSets.ChallengeSet1.challenge
    ).exists()
    response = get_view_for_user(
        viewname="participants:registration-create",
        client=client,
        method=client.post,
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        user=user,
    )
    assert response.status_code == 302
    assert RegistrationRequest.objects.filter(
        user=user, challenge=TwoChallengeSets.ChallengeSet1.challenge
    ).exists()


@pytest.mark.django_db
def test_duplicate_registration_denied(client, TwoChallengeSets):
    user = UserFactory()
    assert not RegistrationRequest.objects.filter(
        user=user, challenge=TwoChallengeSets.ChallengeSet1.challenge
    ).exists()
    rr = RegistrationRequestFactory(
        user=user, challenge=TwoChallengeSets.ChallengeSet1.challenge
    )
    assert RegistrationRequest.objects.filter(
        user=user, challenge=TwoChallengeSets.ChallengeSet1.challenge
    ).exists()
    response = get_view_for_user(
        viewname="participants:registration-create",
        client=client,
        method=client.post,
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        user=user,
    )
    assert response.status_code == 200
    assert rr.status_to_string() in response.rendered_content
    # Creating a request in another challenge should work
    assert not RegistrationRequest.objects.filter(
        user=user, challenge=TwoChallengeSets.ChallengeSet2.challenge
    ).exists()
    response = get_view_for_user(
        viewname="participants:registration-create",
        client=client,
        method=client.post,
        challenge=TwoChallengeSets.ChallengeSet2.challenge,
        user=user,
    )
    assert response.status_code == 302
    assert RegistrationRequest.objects.filter(
        user=user, challenge=TwoChallengeSets.ChallengeSet2.challenge
    ).exists()
