import binascii

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from knox.crypto import hash_token
from knox.models import AuthToken
from rest_framework import exceptions
from rest_framework.authentication import (
    TokenAuthentication as BaseTokenAuthentication,
)


class TokenAuthentication(BaseTokenAuthentication):
    model = AuthToken
    keyword = "Bearer"

    def authenticate_credentials(self, key):
        try:
            hashed_key = hash_token(key)
        except (TypeError, binascii.Error):
            raise exceptions.AuthenticationFailed(_("Invalid token."))

        user, token = super().authenticate_credentials(key=hashed_key)

        if token.expiry is not None and token.expiry < timezone.now():
            raise exceptions.AuthenticationFailed(_("Invalid token."))

        return (user, token)
