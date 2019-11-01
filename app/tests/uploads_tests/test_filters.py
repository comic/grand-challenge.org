import pytest

from tests.factories import UploadFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_upload_list_is_filtered(client, two_challenge_sets):
    u1 = UploadFactory(challenge=two_challenge_sets.challenge_set_1.challenge)
    u2 = UploadFactory(challenge=two_challenge_sets.challenge_set_2.challenge)
    response = get_view_for_user(
        viewname="uploads:list",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        user=two_challenge_sets.admin12,
    )
    assert u1.file.name in response.rendered_content
    assert u2.file.name not in response.rendered_content
