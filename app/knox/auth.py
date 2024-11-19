import binascii

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from knox.crypto import hash_token
from knox.models import AuthToken
from rest_framework import exceptions
from rest_framework.authentication import (
    BaseAuthentication,
    get_authorization_header,
)


class TokenAuthentication(BaseAuthentication):
    """
    Uses Knox AuthTokens for authentication.

    Similar to DRF's TokenAuthentication, it overrides a large amount of that
    authentication scheme to cope with the fact that Tokens are not stored
    in plaintext in the database

    If successful
    - `request.user` will be a django `User` instance
    - `request.auth` will be an `AuthToken` instance
    """

    model = AuthToken

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        prefix = self.authenticate_header(request).encode()

        if not auth:
            return None
        if auth[0].lower() != prefix.lower():
            # Authorization header is possibly for another backend
            return None
        if len(auth) == 1:
            msg = _("Invalid token header. No credentials provided.")
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _(
                "Invalid token header. "
                "Token string should not contain spaces."
            )
            raise exceptions.AuthenticationFailed(msg)

        user, auth_token = self.authenticate_credentials(auth[1])
        return (user, auth_token)

    def authenticate_credentials(self, token):
        msg = _("Invalid token.")
        token = token.decode("utf-8")

        try:
            digest = hash_token(token)
        except (TypeError, binascii.Error):
            raise exceptions.AuthenticationFailed(msg)

        try:
            auth_token = AuthToken.objects.get(digest=digest)
        except AuthToken.DoesNotExist:
            raise exceptions.AuthenticationFailed(msg)

        if self._cleanup_token(auth_token):
            raise exceptions.AuthenticationFailed(msg)

        return self.validate_user(auth_token)

    def validate_user(self, auth_token):
        if not auth_token.user.is_active:
            raise exceptions.AuthenticationFailed(
                _("User inactive or deleted.")
            )
        return (auth_token.user, auth_token)

    def authenticate_header(self, request):
        return "Bearer"

    def _cleanup_token(self, auth_token):
        for other_token in auth_token.user.auth_token_set.all():
            if other_token.digest != auth_token.digest and other_token.expiry:
                if other_token.expiry < timezone.now():
                    other_token.delete()
        if auth_token.expiry is not None:
            if auth_token.expiry < timezone.now():
                auth_token.delete()
                return True
        return False
