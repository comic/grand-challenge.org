import factory

from grandchallenge.emails.models import Email


class EmailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Email
