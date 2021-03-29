import factory
from django.contrib.flatpages.models import FlatPage
from django.contrib.redirects.models import Redirect


class FlatPageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FlatPage


class RedirectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Redirect
