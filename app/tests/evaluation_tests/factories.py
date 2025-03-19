import factory

from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.evaluation.models import (
    CombinedLeaderboard,
    Evaluation,
    EvaluationGroundTruth,
    EvaluationInputSet,
    Method,
    Phase,
    Submission,
)
from tests.components_tests.factories import ComponentInterfaceValueFactory
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
    algorithm_requires_memory_gb = 4
    algorithm_requires_gpu_type = GPUTypeChoices.NO_GPU


class EvaluationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Evaluation

    method = factory.SubFactory(MethodFactory)
    submission = factory.SubFactory(SubmissionFactory)
    requires_memory_gb = 4
    requires_gpu_type = GPUTypeChoices.NO_GPU


class CombinedLeaderboardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CombinedLeaderboard

    challenge = factory.SubFactory(ChallengeFactory)
    title = factory.sequence(lambda n: f"Combined Leaderboard {n}")


class EvaluationGroundTruthFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EvaluationGroundTruth

    phase = factory.SubFactory(PhaseFactory)
    creator = factory.SubFactory(UserFactory)
    ground_truth = factory.django.FileField()
    sha256 = factory.sequence(lambda n: hash_sha256(f"ground_truth{n}"))


class EvaluationInputSetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EvaluationInputSet

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        inputs = kwargs.pop("inputs", None)
        if not inputs:
            inputs = [ComponentInterfaceValueFactory()]
        return manager.create(*args, inputs=inputs, **kwargs)
