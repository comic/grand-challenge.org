from textwrap import dedent

import pytest
from guardian.shortcuts import assign_perm

from tests.evaluation_tests.factories import SubmissionFactory
from tests.factories import (
    ImageFileFactory,
    UserFactory,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize("cloudfront", (True, False))
def test_image_response(client, settings, cloudfront, tmpdir):
    pem = tmpdir.join("cf.pem")
    pem.write(
        dedent(
            """
            -----BEGIN RSA PRIVATE KEY-----
            MIICXQIBAAKBgQDA7ki9gI/lRygIoOjV1yymgx6FYFlzJ+z1ATMaLo57nL57AavW
            hb68HYY8EA0GJU9xQdMVaHBogF3eiCWYXSUZCWM/+M5+ZcdQraRRScucmn6g4EvY
            2K4W2pxbqH8vmUikPxir41EeBPLjMOzKvbzzQy9e/zzIQVREKSp/7y1mywIDAQAB
            AoGABc7mp7XYHynuPZxChjWNJZIq+A73gm0ASDv6At7F8Vi9r0xUlQe/v0AQS3yc
            N8QlyR4XMbzMLYk3yjxFDXo4ZKQtOGzLGteCU2srANiLv26/imXA8FVidZftTAtL
            viWQZBVPTeYIA69ATUYPEq0a5u5wjGyUOij9OWyuy01mbPkCQQDluYoNpPOekQ0Z
            WrPgJ5rxc8f6zG37ZVoDBiexqtVShIF5W3xYuWhW5kYb0hliYfkq15cS7t9m95h3
            1QJf/xI/AkEA1v9l/WN1a1N3rOK4VGoCokx7kR2SyTMSbZgF9IWJNOugR/WZw7HT
            njipO3c9dy1Ms9pUKwUF46d7049ck8HwdQJARgrSKuLWXMyBH+/l1Dx/I4tXuAJI
            rlPyo+VmiOc7b5NzHptkSHEPfR9s1OK0VqjknclqCJ3Ig86OMEtEFBzjZQJBAKYz
            470hcPkaGk7tKYAgP48FvxRsnzeooptURW5E+M+PQ2W9iDPPOX9739+Xi02hGEWF
            B0IGbQoTRFdE4VVcPK0CQQCeS84lODlC0Y2BZv2JxW3Osv/WkUQ4dslfAQl1T303
            7uwwr7XTroMv8dIFQIPreoPhRKmd/SbJzbiKfS/4QDhU
            -----END RSA PRIVATE KEY-----
            """
        )
    )

    settings.CLOUDFRONT_PRIVATE_KEY_PATH = pem.strpath
    settings.CLOUDFRONT_KEY_PAIR_ID = "PK123456789754"
    settings.PROTECTED_S3_STORAGE_USE_CLOUDFRONT = cloudfront

    image_file = ImageFileFactory()
    user = UserFactory()

    response = get_view_for_user(
        url=image_file.file.url, client=client, user=user
    )

    # Forbidden view
    assert response.status_code == 403
    assert not response.has_header("x-accel-redirect")

    assign_perm("view_image", user, image_file.image)

    response = get_view_for_user(
        url=image_file.file.url, client=client, user=user
    )

    assert response.status_code == 302
    assert not response.has_header("x-accel-redirect")

    redirect = response.url

    if cloudfront:
        assert redirect.startswith(
            f"https://{settings.PROTECTED_S3_STORAGE_CLOUDFRONT_DOMAIN}/"
        )

        assert "AWSAccessKeyId" not in redirect
        assert "Signature" in redirect
        assert "Expires" in redirect
    else:
        assert redirect.startswith(
            f"{settings.PROTECTED_S3_STORAGE_KWARGS['endpoint_url']}/"
            f"{settings.PROTECTED_S3_STORAGE_KWARGS['bucket_name']}/"
        )

        assert "AWSAccessKeyId" in redirect
        assert "Signature" in redirect
        assert "Expires" in redirect


@pytest.mark.django_db
def test_submission_download(client, two_challenge_sets):
    """Only the challenge admin should be able to download submissions."""
    submission = SubmissionFactory(
        phase=two_challenge_sets.challenge_set_1.challenge.phase_set.get(),
        creator=two_challenge_sets.challenge_set_1.participant,
    )

    tests = [
        # (
        #   image response + annotation response not test ground truth,
        #   user
        # )
        (403, None),
        (403, two_challenge_sets.challenge_set_1.non_participant),
        (302, two_challenge_sets.challenge_set_1.participant),
        (403, two_challenge_sets.challenge_set_1.participant1),
        (302, two_challenge_sets.challenge_set_1.creator),
        (302, two_challenge_sets.challenge_set_1.admin),
        (403, two_challenge_sets.challenge_set_2.non_participant),
        (403, two_challenge_sets.challenge_set_2.participant),
        (403, two_challenge_sets.challenge_set_2.participant1),
        (403, two_challenge_sets.challenge_set_2.creator),
        (403, two_challenge_sets.challenge_set_2.admin),
        (302, two_challenge_sets.admin12),
        (403, two_challenge_sets.participant12),
        (302, two_challenge_sets.admin1participant2),
    ]

    for test in tests:
        response = get_view_for_user(
            url=submission.predictions_file.url, client=client, user=test[1]
        )
        assert response.status_code == test[0]
