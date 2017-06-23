import json

import pytest
from django.utils.encoding import force_text
from rest_framework.authtoken.models import Token

from .factories import UserFactory
from ..models import Submission

TOKEN_URL = '/evaluation/api-token-auth/'


@pytest.mark.django_db
@pytest.mark.parametrize(
    "test_input, expected",
    [("results", "Result List"),
     ("submissions", "Submission List"),
     ("jobs", "Job List"),
     ("methods", "Method List")]
)
def test_result_list(client, test_input, expected):
    # Check for the correct HTML view
    response = client.get('/evaluation/api/v1/%s/' % test_input,
                          HTTP_ACCEPT='text/html')
    assert expected in force_text(response.content)
    assert response.status_code == 200

    # There should be no content, but we should be able to do json.loads
    response = client.get('/evaluation/api/v1/%s/' % test_input,
                          HTTP_ACCEPT='application/json')
    assert response.status_code == 200
    assert not json.loads(response.content)


@pytest.mark.django_db
def test_token_generation(client):
    # Check that we cannot get a token
    response = client.get(TOKEN_URL)
    assert response.status_code == 405

    # Check that we can get the token for a new user, using post
    user = UserFactory()
    response = client.post(TOKEN_URL,
                           {'username': user.username,
                            'password': 'testpasswd'})

    assert response.data['token'] == Token.objects.get(
        user__username=user.username).key
    assert response.status_code == 200


@pytest.mark.django_db
def test_upload_file(client):
    # Get the users token
    user = UserFactory()
    response = client.post(TOKEN_URL,
                           {'username': user.username,
                            'password': 'testpasswd'})
    token = response.data['token']

    # Upload with token authorisation
    with open(
            '/tmp/google-analytics-tracking.js.template',
            'rb') as f:
        response = client.post('/evaluation/api/v1/submissions/',
                               {'file': f, 'challenge': 'comic'},
                               format='multipart',
                               HTTP_AUTHORIZATION='Token ' + token)
    assert response.status_code == 201

    # Upload with session authorisation
    client.login(username=user.username, password='testpasswd')
    with open(
            '/tmp/google-analytics-tracking.js.template',
            'rb') as f:
        response = client.post('/evaluation/api/v1/submissions/',
                               {'file': f, 'challenge': 'comic'},
                               format='multipart')
    assert response.status_code == 201

    submissions = Submission.objects.all()
    assert len(submissions) == 2

    # TODO: Validate the file and path
    # TODO: Get the challenge name from the URL
    # TODO: Check that the user is a participant of that challenge
