import pytest

from tests.factories import RegistrationRequestFactory, UserFactory


@pytest.mark.django_db
def test_registration_workflow_no_review(ChallengeSet):
    user = UserFactory()

    ChallengeSet.challenge.require_participant_review = False
    ChallengeSet.challenge.save()

    RegistrationRequestFactory(project=ChallengeSet.challenge, user=user)

    assert ChallengeSet.challenge.is_participant(user)
