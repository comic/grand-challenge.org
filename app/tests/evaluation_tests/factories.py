from factory import DjangoModelFactory, SubFactory

from grandchallenge.evaluation.models import AlgorithmEvaluation
from tests.factories import SubmissionFactory


class AlgorithmEvaluationFactory(DjangoModelFactory):
    class Meta:
        model = AlgorithmEvaluation

    submission = SubFactory(SubmissionFactory)
