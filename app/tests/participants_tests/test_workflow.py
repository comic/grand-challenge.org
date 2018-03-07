import pytest

from comicmodels.models import RegistrationRequest
from tests.factories import RegistrationRequestFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_registration_no_review_workflow(ChallengeSet):
    user = UserFactory()

    ChallengeSet.challenge.require_participant_review = False
    ChallengeSet.challenge.save()

    RegistrationRequestFactory(project=ChallengeSet.challenge, user=user)

    assert ChallengeSet.challenge.is_participant(user)


@pytest.mark.django_db
def test_registration_review_workflow(client, ChallengeSet):
    user = UserFactory()

    ChallengeSet.challenge.require_participant_review = True
    ChallengeSet.challenge.save()

    rr = RegistrationRequestFactory(project=ChallengeSet.challenge, user=user)

    assert not ChallengeSet.challenge.is_participant(user)

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname='participants:registration-update',
        challenge=ChallengeSet.challenge,
        user=ChallengeSet.admin,
        reverse_kwargs={'pk': rr.pk},
        data={'status': RegistrationRequest.ACCEPTED},
    )

    assert response.status_code == 302
    assert ChallengeSet.challenge.is_participant(user)
