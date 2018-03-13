import pytest

from comicmodels.models import UploadModel
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_upload_with_ckeditor(client, tmpdir, TwoChallengeSets):
    filename = 'hello.txt'

    p = tmpdir.mkdir("sub").join(filename)
    p.write("content")

    num_files = UploadModel.objects.all().count()

    with open(p, 'rb') as f:
        response = get_view_for_user(
            viewname='uploads:ck-create',
            challenge=TwoChallengeSets.ChallengeSet1.challenge,
            user=TwoChallengeSets.admin12,
            client=client,
            method=client.post,
            data={
                'upload': f,
            },
            format='multipart',
        )

    assert response.status_code == 302
    assert UploadModel.objects.all().count() == num_files + 1
