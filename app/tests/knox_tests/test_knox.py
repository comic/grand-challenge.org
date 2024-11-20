from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from knox.auth import TokenAuthentication
from knox.models import AuthToken, hash_token
from knox.settings import CONSTANTS
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory
from rest_framework.test import APITestCase as TestCase

from tests.factories import UserFactory

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
        instance, token = AuthToken.objects.create(user=self.user)
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
        instance, token = AuthToken.objects.create(user=self.user)
        odd_length_token = token + "1"
        self.client.credentials(
            HTTP_AUTHORIZATION=("Bearer %s" % odd_length_token)
        )
        response = self.client.post(root_url, {}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, {"detail": "Invalid token."})

    def test_token_expiry_is_not_extended(self):
        instance, token = AuthToken.objects.create(user=self.user)

        original_expiry = AuthToken.objects.get().expiry

        self.client.credentials(HTTP_AUTHORIZATION=("Bearer %s" % token))
        response = self.client.get(root_url, {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(original_expiry, AuthToken.objects.get().expiry)

    def test_invalid_prefix_return_401(self):
        instance, token = AuthToken.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=("Baerer %s" % token))
        failed_response = self.client.get(root_url)
        self.client.credentials(HTTP_AUTHORIZATION=("Bearer %s" % token))
        response = self.client.get(root_url)
        self.assertEqual(failed_response.status_code, 401)
        self.assertEqual(response.status_code, 200)

    def test_tokens_still_work(self):
        self.assertEqual(AuthToken.objects.count(), 0)

        old_token = (
            "02d233c901e7bd38df1dbc486b7e22c5c81b089c40cbb31d35d7b032615f5778"
        )
        # Hash generated using crypto.hash_token on 4.2.0 with
        # SECURE_HASH_ALGORITHM = 'cryptography.hazmat.primitives.hashes.SHA512'
        old_key = "d74a4d2e7b8cb90e432aba33d75b8a6d803091d5a5d758d0ae70558573ceae01439cffbe43182470b73e7001dbbd96cbf12cbcbebe36b24cf4c4cb3198b936fc"

        AuthToken(key=old_key, user=self.user).save()

        rf = APIRequestFactory()
        request = rf.get("/")
        request.META = {"HTTP_AUTHORIZATION": f"Bearer {old_token}"}
        user, auth_token = TokenAuthentication().authenticate(request)
        self.assertEqual(self.user, user)
        self.assertEqual(old_key, auth_token.key)


@pytest.mark.django_db
def test_token_lengths():
    user = UserFactory()

    _, token = AuthToken.objects.create(user=user, expiry=None)

    auth_token = user.auth_token_set.get()

    assert auth_token.user == user
    assert auth_token.key == hash_token(token)
    assert auth_token.token_key == token[:8]
    assert auth_token.expiry is None
    assert len(auth_token.key) == 128  # Matches what is used in models.py
    assert len(auth_token.token_key) == 8
    assert len(token) == 64


@pytest.mark.django_db
def test_default_expiry():
    user = UserFactory()

    auth_token, _ = AuthToken.objects.create(user=user)

    assert (
        auth_token.expiry - auth_token.created
    ).total_seconds() == pytest.approx(timedelta(hours=10).total_seconds())


@pytest.mark.django_db
def test_provided_expiry():
    user = UserFactory()

    auth_token, _ = AuthToken.objects.create(
        user=user, expiry=timedelta(hours=100)
    )

    assert (
        auth_token.expiry - auth_token.created
    ).total_seconds() == pytest.approx(timedelta(hours=100).total_seconds())
