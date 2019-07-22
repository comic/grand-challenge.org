import factory

from grandchallenge.reader_studies.models import ReaderStudy, Question, Answer
from tests.factories import UserFactory


class ReaderStudyFactory(factory.DjangoModelFactory):
    class Meta:
        model = ReaderStudy

    creator = factory.SubFactory(UserFactory)


class QuestionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Question

    reader_study = factory.SubFactory(ReaderStudyFactory)


class AnswerFactory(factory.DjangoModelFactory):
    class Meta:
        model = Answer

    creator = factory.SubFactory(UserFactory)
    question = factory.SubFactory(QuestionFactory)
