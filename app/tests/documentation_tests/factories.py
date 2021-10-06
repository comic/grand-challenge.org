import factory
from faker import Faker

from grandchallenge.documentation.models import DocPage


faker = Faker()


class DocPageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocPage

    title = factory.Sequence(lambda n: f"page_{n}")
    content = factory.LazyAttribute(lambda t: faker.text(max_nb_chars=200))
