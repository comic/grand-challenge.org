from django.contrib.auth import get_user_model
from rest_framework.fields import CharField
from rest_framework.serializers import ModelSerializer

from grandchallenge.api.swagger import swagger_schema_fields_for_charfield
from grandchallenge.challenges.models import Challenge
from grandchallenge.components.serializers import (
    ComponentInterfaceValueSerializer,
)
from grandchallenge.evaluation.models import (
    AlgorithmEvaluation,
    Evaluation,
    Phase,
    Submission,
)


class UserSerializer(ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("username",)


class ChallengeSerializer(ModelSerializer):
    class Meta:
        model = Challenge
        fields = (
            "title",
            "short_name",
        )


class PhaseSerializer(ModelSerializer):
    challenge = ChallengeSerializer()

    class Meta:
        model = Phase
        fields = (
            "challenge",
            "title",
            "slug",
        )


class SubmissionSerializer(ModelSerializer):
    phase = PhaseSerializer()
    creator = UserSerializer()

    class Meta:
        model = Submission
        fields = (
            "pk",
            "phase",
            "created",
            "creator",
            "comment",
            "predictions_file",
            "supplementary_file",
            "publication_url",
        )


class AlgorithmEvaluationSerializer(ModelSerializer):
    inputs = ComponentInterfaceValueSerializer(many=True)
    outputs = ComponentInterfaceValueSerializer(many=True)

    class Meta:
        model = AlgorithmEvaluation
        fields = (
            "pk",
            "inputs",
            "outputs",
        )


class EvaluationSerializer(ModelSerializer):
    submission = SubmissionSerializer()
    status = CharField(source="get_status_display", read_only=True)
    outputs = ComponentInterfaceValueSerializer(many=True)

    class Meta:
        model = Evaluation
        fields = (
            "pk",
            "method",
            "submission",
            "created",
            "published",
            "outputs",
            "rank",
            "rank_score",
            "rank_per_metric",
            "status",
        )
        swagger_schema_fields = swagger_schema_fields_for_charfield(
            status=model._meta.get_field("status")
        )
