import pytest

from tests.factories import UploadFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_upload_list_is_filtered(client, TwoChallengeSets):
    u1 = UploadFactory(challenge=TwoChallengeSets.ChallengeSet1.challenge)
    u2 = UploadFactory(challenge=TwoChallengeSets.ChallengeSet2.challenge)
    response = get_view_for_user(
        viewname="uploads:list",
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        user=TwoChallengeSets.admin12,
    )
    assert u1.file.name in response.rendered_content
    assert u2.file.name not in response.rendered_content
