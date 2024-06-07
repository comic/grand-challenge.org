import factory

from grandchallenge.evaluation.models import (
    CombinedLeaderboard,
    Evaluation,
    GroundTruth,
    Method,
    Phase,
    Submission,
)
from tests.factories import ChallengeFactory, UserFactory, hash_sha256


class PhaseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Phase

    challenge = factory.SubFactory(ChallengeFactory)
    title = factory.sequence(lambda n: f"Phase {n}")


class MethodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Method

    creator = factory.SubFactory(UserFactory)
    phase = factory.SubFactory(PhaseFactory)
    image = factory.django.FileField()
    image_sha256 = factory.sequence(lambda n: hash_sha256(f"image{n}"))


class SubmissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Submission

    phase = factory.SubFactory(PhaseFactory)
    predictions_file = factory.django.FileField()
    creator = factory.SubFactory(UserFactory)


class EvaluationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Evaluation

    method = factory.SubFactory(MethodFactory)
    submission = factory.SubFactory(SubmissionFactory)


class CombinedLeaderboardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CombinedLeaderboard

    challenge = factory.SubFactory(ChallengeFactory)
    title = factory.sequence(lambda n: f"Combined Leaderboard {n}")


class GroundTruthFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroundTruth

    phase = factory.SubFactory(PhaseFactory)
    creator = factory.SubFactory(UserFactory)
    ground_truth = factory.django.FileField()
    sha256 = factory.sequence(lambda n: hash_sha256(f"ground_truth{n}"))
