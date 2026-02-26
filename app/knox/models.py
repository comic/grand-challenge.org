import binascii
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from knox.settings import CONSTANTS

User = settings.AUTH_USER_MODEL
DEFAULT_EXPIRY = timedelta(hours=10)


def hash_token(token):
    return hashlib.sha512(binascii.unhexlify(token)).hexdigest()


class AuthTokenManager(models.Manager):
    def create(self, *, user, expiry=DEFAULT_EXPIRY):
        token = secrets.token_hex()
        key = hash_token(token)

        if expiry is not None:
            expiry = timezone.now() + expiry

        instance = super().create(
            key=key,
            token_key=token[: CONSTANTS.TOKEN_KEY_LENGTH],
            user=user,
            expiry=expiry,
        )
        return instance, token

    def get_active(self, *, user=None):
        qs = self.filter(
            models.Q(expiry__isnull=True) | models.Q(expiry__gt=timezone.now())
        )
        if user is not None:
            qs = qs.filter(user=user)
        return qs

    def get_expired(self, *, user=None):
        qs = self.filter(expiry__lte=timezone.now())
        if user is not None:
            qs = qs.filter(user=user)
        return qs

    def purge_expired(self, *, user=None):
        return self.get_expired(user=user).delete()


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
    last_used = models.DateTimeField(null=True, blank=True)
    use_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.key} : {self.user}"

    @property
    def is_expired(self):
        if self.expiry is None:
            return False
        return timezone.now() >= self.expiry

    @property
    def time_remaining(self):
        if self.expiry is None:
            return None
        delta = self.expiry - timezone.now()
        return delta if delta.total_seconds() > 0 else timedelta(0)

    def update_last_used(self):
        now = timezone.now()
        AuthToken.objects.filter(pk=self.pk).update(
            last_used=now,
            use_count=models.F("use_count") + 1,
        )
        self.last_used = now
        self.use_count += 1

    def rotate(self, expiry=DEFAULT_EXPIRY):
        new_instance, new_token = AuthToken.objects.create(
            user=self.user,
            expiry=expiry,
        )
        self.delete()
        return new_instance, new_token
