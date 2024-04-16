import factory

from grandchallenge.emails.models import Email, RawEmail


class EmailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Email


class RawEmailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RawEmail
