import factory

from grandchallenge.uploads.models import UserUpload
from tests.factories import UserFactory


class UserUploadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserUpload

    creator = factory.SubFactory(UserFactory)
