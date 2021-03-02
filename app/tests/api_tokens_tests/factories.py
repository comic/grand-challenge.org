from factory import SubFactory
from factory.django import DjangoModelFactory
from knox.models import AuthToken

from tests.factories import UserFactory


class AuthTokenFactory(DjangoModelFactory):
    class Meta:
        model = AuthToken

    user = SubFactory(UserFactory)
