from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from knox import crypto
from knox.settings import CONSTANTS

User = settings.AUTH_USER_MODEL
DEFAULT_EXPIRY = timedelta(hours=10)


class AuthTokenManager(models.Manager):
    def create(self, user, expiry=DEFAULT_EXPIRY):
        token = crypto.create_token_string()
        key = crypto.hash_token(token)

        if expiry is not None:
            expiry = timezone.now() + expiry

        instance = super().create(
            key=key,
            token_key=token[: CONSTANTS.TOKEN_KEY_LENGTH],
            user=user,
            expiry=expiry,
        )
        return instance, token


class AuthToken(models.Model):

    objects = AuthTokenManager()

    key = models.CharField(max_length=128, primary_key=True)
    token_key = models.CharField(
        max_length=CONSTANTS.TOKEN_KEY_LENGTH, db_index=True
    )
    user = models.ForeignKey(
        User,
        null=False,
        blank=False,
        related_name="auth_token_set",
        on_delete=models.CASCADE,
    )
    created = models.DateTimeField(auto_now_add=True)
    expiry = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.key} : {self.user}"
