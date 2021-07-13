from django.contrib.auth import get_user_model
from rest_framework.fields import CharField
from rest_framework.serializers import ModelSerializer

from grandchallenge.challenges.models import Challenge
from grandchallenge.components.serializers import (
    ComponentInterfaceValueSerializer,
)
from grandchallenge.evaluation.models import (
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
            "supplementary_url",
        )


class EvaluationSerializer(ModelSerializer):
    submission = SubmissionSerializer()
    outputs = ComponentInterfaceValueSerializer(many=True)
    status = CharField(source="get_status_display", read_only=True)
    title = CharField(read_only=True)

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
            "title",
        )
