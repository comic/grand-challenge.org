import factory

from grandchallenge.reader_studies.models import ReaderStudy
from tests.factories import UserFactory


class ReaderStudyFactory(factory.DjangoModelFactory):
    class Meta:
        model = ReaderStudy

    creator = factory.SubFactory(UserFactory)
