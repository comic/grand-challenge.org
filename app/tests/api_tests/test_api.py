import json
import os

import pytest
from django.conf import settings
from django.utils.encoding import force_text
from rest_framework.authtoken.models import Token

from grandchallenge.evaluation.models import Submission
from grandchallenge.subdomains.utils import reverse
from tests.factories import UserFactory, ChallengeFactory


def get_staff_user_with_token():
    user = UserFactory(is_staff=True)
    token = Token.objects.create(user=user)

    return user, token.key


@pytest.mark.django_db
@pytest.mark.parametrize(
    "test_input, expected",
    [("submission", "Submission List"), ("image", "Image List")],
)
def test_api_pages(client, test_input, expected):
    _, token = get_staff_user_with_token()

    # Check for the correct HTML view
    url = reverse(f"api:{test_input}-list")
    response = client.get(
        url, HTTP_ACCEPT="text/html", HTTP_AUTHORIZATION="Token " + token
    )
    assert expected in force_text(response.content)
    assert response.status_code == 200

    # There should be no content, but we should be able to do json.loads
    response = client.get(
        url,
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token,
    )
    assert response.status_code == 200
    assert not json.loads(response.content)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "test_file, expected_response",
    [("compressed.zip", 201), ("compressed.7z", 400)],
)
def test_upload_file(client, test_file, expected_response):
    submission_file = os.path.join(
        os.path.split(__file__)[0], "resources", test_file
    )

    # Get the users token
    user, token = get_staff_user_with_token()

    challenge = ChallengeFactory()
    submission_url = reverse("api:submission-list")

    # Upload with token authorisation
    with open(submission_file, "rb") as f:
        response = client.post(
            submission_url,
            {"file": f, "challenge": challenge.short_name},
            format="multipart",
            HTTP_AUTHORIZATION="Token " + token,
        )
    assert response.status_code == expected_response

    submissions = Submission.objects.all()
    if expected_response == 201:
        assert len(submissions) == 1
    else:
        assert len(submissions) == 0

    # We should not be able to download submissions
    for submission in Submission.objects.all():
        response = client.get(submission.file.url)
        assert response.status_code == 404

    # Cleanup
    for submission in submissions:
        filepath = submission.file.name
        submission.file.delete()
        try:
            os.removedirs(settings.MEDIA_ROOT + os.path.split(filepath)[0])
        except OSError:
            pass
