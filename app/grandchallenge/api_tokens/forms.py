from django.forms import Form
from knox.models import AuthToken

from grandchallenge.core.forms import SaveFormInitMixin


class AuthTokenForm(SaveFormInitMixin, Form):
    def create_token(self, *, user):
        return AuthToken.objects.create(user=user, expiry=None)
