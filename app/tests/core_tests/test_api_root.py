from rest_framework.test import APITestCase


class RootTest(APITestCase):
    def test_root(self):
        return
        url = '/api/v1/'
        response = self.client.get(url, format="json")
        self.assertEqual(401, response.status_code)
        self.assertDictEqual(response.data, {"detail": "Authentication credentials were not provided."})