from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from tests.factories import UserFactory


class RootTest(APITestCase):
    def test_root(self):
        url = '/api/v1/me/'
        response = self.client.get(url, format="json")
        self.assertEqual(401, response.status_code)
        self.assertDictEqual(response.data, {"detail": "Authentication credentials were not provided."})

    def test_me_route(self):
        user = UserFactory()
        token, created = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + str(token))
        url = '/api/v1/me/'
        response = self.client.get(url, format="json")
        self.assertEqual(user.id, response.json()['id'])
