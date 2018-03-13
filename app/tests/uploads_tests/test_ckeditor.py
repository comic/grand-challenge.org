import pytest

from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_upload_with_ckeditor(client, tmpdir, TwoChallengeSets):
    p = tmpdir.mkdir("sub").join("hello.txt")
    p.write("content")

    response = get_view_for_user(
        viewname='uploads:ck-create',
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        user=TwoChallengeSets.admin12,
        client=client,
    )

    assert response.status_code == 200

