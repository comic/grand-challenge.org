import factory

from grandchallenge.publications.models import Publication


class PublicationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Publication

    csl = {
        "type": "journal-article",
        "title": "doi title",
    }
    year = factory.Faker("year")
