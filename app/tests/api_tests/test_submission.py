from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from tests.factories import UserFactory


class SubmissionCreateTest(APITestCase):
    def test_validation_errors(self):
        user = UserFactory()
        token, created = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + str(token))
        url = '/api/v1/submissions/'
        data = {
            'name': "bladiebla",
            'benchmark': 123,
        }
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(400, response.status_code)
        self.assertEqual(response.data['benchmark'][0]['code'], 'does_not_exist')
        self.assertEqual(response.data['implementation'][0]['code'], 'required')
