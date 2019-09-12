from guardian.shortcuts import assign_perm
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from comic.eyra_algorithms.models import Algorithm
from tests.factories import UserFactory, AlgorithmFactory


class AlgorithmApiTest(APITestCase):
    def test_array_field(self):
        user = UserFactory()
        token, created = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + str(token))
        algorithm: Algorithm = AlgorithmFactory(
            creator=user
        )
        assign_perm('eyra_algorithms.view_algorithm', user)
        url = f'/api/v1/algorithms/{algorithm.id}/'
        response = self.client.get(url, format="json")
        self.assertEqual(200, response.status_code)
        self.assertIsInstance(response.data['tags'], list)
