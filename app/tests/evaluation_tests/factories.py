import factory.django
from factory import DjangoModelFactory, SubFactory

from grandchallenge.evaluation.models import (
    AlgorithmEvaluation,
    Evaluation,
    Method,
    Phase,
    Submission,
)
from tests.factories import ChallengeFactory, UserFactory, hash_sha256


class PhaseFactory(factory.DjangoModelFactory):
    class Meta:
        model = Phase

    challenge = factory.SubFactory(ChallengeFactory)
    title = factory.sequence(lambda n: f"Phase {n}")


class MethodFactory(factory.DjangoModelFactory):
    class Meta:
        model = Method

    phase = factory.SubFactory(PhaseFactory)
    image = factory.django.FileField()
    image_sha256 = factory.sequence(lambda n: hash_sha256(f"image{n}"))


class SubmissionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Submission

    phase = factory.SubFactory(PhaseFactory)
    predictions_file = factory.django.FileField()
    creator = factory.SubFactory(UserFactory)


class AlgorithmEvaluationFactory(DjangoModelFactory):
    class Meta:
        model = AlgorithmEvaluation

    submission = SubFactory(SubmissionFactory)


class EvaluationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Evaluation

    method = factory.SubFactory(MethodFactory)
    submission = factory.SubFactory(SubmissionFactory)
