import factory

from grandchallenge.reader_studies.models import Answer, Question, ReaderStudy
from tests.factories import UserFactory, WorkstationFactory


class ReaderStudyFactory(factory.DjangoModelFactory):
    class Meta:
        model = ReaderStudy

    title = factory.Sequence(lambda n: f"test_reader_study_{n:04}")
    logo = factory.django.ImageField()
    workstation = factory.SubFactory(WorkstationFactory)


class QuestionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Question

    reader_study = factory.SubFactory(ReaderStudyFactory)


class AnswerFactory(factory.DjangoModelFactory):
    class Meta:
        model = Answer

    creator = factory.SubFactory(UserFactory)
    question = factory.SubFactory(QuestionFactory)
