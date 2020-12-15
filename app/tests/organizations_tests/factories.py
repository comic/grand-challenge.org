import factory

from grandchallenge.organizations.models import Organization


class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization

    title = factory.Faker("company")
    logo = factory.django.ImageField()
