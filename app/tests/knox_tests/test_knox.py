from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from freezegun import freeze_time
from knox.auth import TokenAuthentication
from knox.models import AuthToken
from knox.settings import CONSTANTS
from knox.signals import token_expired
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory
from rest_framework.test import APITestCase as TestCase

User = get_user_model()
root_url = reverse("knox-api-root")


class AuthTestCase(TestCase):

    def setUp(self):
        self.username = "john.doe"
        self.email = "john.doe@example.com"
        self.password = "hunter2"
        self.user = User.objects.create_user(
            self.username, self.email, self.password
        )

        self.username2 = "jane.doe"
        self.email2 = "jane.doe@example.com"
        self.password2 = "hunter2"
        self.user2 = User.objects.create_user(
            self.username2, self.email2, self.password2
        )

    def test_expired_tokens_login_fails(self):
        self.assertEqual(AuthToken.objects.count(), 0)
        instance, token = AuthToken.objects.create(
            user=self.user, expiry=timedelta(seconds=-1)
        )
        self.client.credentials(HTTP_AUTHORIZATION=("Bearer %s" % token))
        response = self.client.post(root_url, {}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, {"detail": "Invalid token."})

    def test_update_token_key(self):
        self.assertEqual(AuthToken.objects.count(), 0)
        instance, token = AuthToken.objects.create(self.user)
        rf = APIRequestFactory()
        request = rf.get("/")
        request.META = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        (self.user, auth_token) = TokenAuthentication().authenticate(request)
        self.assertEqual(
            token[: CONSTANTS.TOKEN_KEY_LENGTH],
            auth_token.token_key,
        )

    def test_authorization_header_empty(self):
        rf = APIRequestFactory()
        request = rf.get("/")
        request.META = {"HTTP_AUTHORIZATION": ""}
        self.assertEqual(TokenAuthentication().authenticate(request), None)

    def test_authorization_header_prefix_only(self):
        rf = APIRequestFactory()
        request = rf.get("/")
        request.META = {"HTTP_AUTHORIZATION": "Bearer"}
        with self.assertRaises(AuthenticationFailed) as err:
            (self.user, auth_token) = TokenAuthentication().authenticate(
                request
            )
        self.assertIn(
            "Invalid token header. No credentials provided.",
            str(err.exception),
        )

    def test_authorization_header_spaces_in_token_string(self):
        rf = APIRequestFactory()
        request = rf.get("/")
        request.META = {"HTTP_AUTHORIZATION": "Bearer wordone wordtwo"}
        with self.assertRaises(AuthenticationFailed) as err:
            (self.user, auth_token) = TokenAuthentication().authenticate(
                request
            )
        self.assertIn(
            "Invalid token header. Token string should not contain spaces.",
            str(err.exception),
        )

    def test_invalid_token_length_returns_401_code(self):
        invalid_token = "1" * (CONSTANTS.TOKEN_KEY_LENGTH - 1)
        self.client.credentials(
            HTTP_AUTHORIZATION=("Bearer %s" % invalid_token)
        )
        response = self.client.post(root_url, {}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, {"detail": "Invalid token."})

    def test_invalid_odd_length_token_returns_401_code(self):
        instance, token = AuthToken.objects.create(self.user)
        odd_length_token = token + "1"
        self.client.credentials(
            HTTP_AUTHORIZATION=("Bearer %s" % odd_length_token)
        )
        response = self.client.post(root_url, {}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, {"detail": "Invalid token."})

    def test_token_expiry_is_not_extended(self):
        now = datetime.now()
        with freeze_time(now):
            instance, token = AuthToken.objects.create(user=self.user)

        original_expiry = AuthToken.objects.get().expiry

        self.client.credentials(HTTP_AUTHORIZATION=("Bearer %s" % token))
        with freeze_time(now + timedelta(hours=1)):
            response = self.client.get(root_url, {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(original_expiry, AuthToken.objects.get().expiry)

    def test_expiry_signals(self):
        self.signal_was_called = False

        def handler(sender, username, **kwargs):
            self.signal_was_called = True

        token_expired.connect(handler)

        instance, token = AuthToken.objects.create(
            user=self.user, expiry=timedelta(seconds=-1)
        )
        self.client.credentials(HTTP_AUTHORIZATION=("Bearer %s" % token))
        self.client.post(root_url, {}, format="json")

        self.assertTrue(self.signal_was_called)

    def test_invalid_prefix_return_401(self):
        instance, token = AuthToken.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=("Baerer %s" % token))
        failed_response = self.client.get(root_url)
        self.client.credentials(HTTP_AUTHORIZATION=("Bearer %s" % token))
        response = self.client.get(root_url)
        self.assertEqual(failed_response.status_code, 401)
        self.assertEqual(response.status_code, 200)
