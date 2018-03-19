import pytest

from tests.factories import UploadFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        'uploads:list',
        'uploads:ck-browse',
    ]
)
def test_upload_list_is_filtered(view, client, TwoChallengeSets):
    u1 = UploadFactory(challenge=TwoChallengeSets.ChallengeSet1.challenge)
    u2 = UploadFactory(challenge=TwoChallengeSets.ChallengeSet2.challenge)

    response = get_view_for_user(
        viewname=view,
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        user=TwoChallengeSets.admin12,
    )

    assert u1.file.name in response.rendered_content
    assert u2.file.name not in response.rendered_content
