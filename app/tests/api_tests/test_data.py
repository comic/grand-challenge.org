from guardian.shortcuts import assign_perm
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from tests.factories import UserFactory, DataFileFactory


class DataFileTest(APITestCase):
    def test_data_file_errors(self):
        user = UserFactory()
        token, created = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + str(token))
        data_file = DataFileFactory(creator=user, name='random file')
        assign_perm('eyra_data.view_datafile', user)

        url = f'/api/v1/data_files/{data_file.id}/'
        response = self.client.get(url, format="json")
        self.assertEqual(200, response.status_code)
