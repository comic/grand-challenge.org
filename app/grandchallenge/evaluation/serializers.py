from django.contrib.auth import get_user_model
from rest_framework.fields import CharField, SerializerMethodField
from rest_framework.relations import HyperlinkedRelatedField
from rest_framework.serializers import ModelSerializer

from grandchallenge.algorithms.serializers import (
    AlgorithmImageSerializer,
    AlgorithmModelSerializer,
)
from grandchallenge.challenges.models import Challenge
from grandchallenge.components.serializers import (
    ComponentInterfaceValuePostSerializer,
    ComponentInterfaceValueSerializer,
)
from grandchallenge.evaluation.models import Evaluation, Phase, Submission


class UserSerializer(ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("username",)


class ChallengeSerializer(ModelSerializer):
    class Meta:
        model = Challenge
        fields = ("title", "short_name")


class PhaseSerializer(ModelSerializer):
    challenge = ChallengeSerializer()

    class Meta:
        model = Phase
        fields = ("challenge", "title", "slug")


class SubmissionSerializer(ModelSerializer):
    phase = PhaseSerializer()
    creator = UserSerializer()
    algorithm_image = HyperlinkedRelatedField(
        read_only=True,
        view_name="api:algorithms-image-detail",
    )

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
            "algorithm_image",
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


class ExternalEvaluationSerializer(EvaluationSerializer):
    algorithm_model = SerializerMethodField()
    algorithm_image = SerializerMethodField()

    class Meta:
        model = Evaluation
        fields = (
            *EvaluationSerializer.Meta.fields,
            "algorithm_model",
            "algorithm_image",
        )

    def get_algorithm_model(self, obj):
        if obj.submission.algorithm_model:
            return AlgorithmModelSerializer(
                obj.submission.algorithm_model, context=self.context
            ).data
        return None

    def get_algorithm_image(self, obj):
        return AlgorithmImageSerializer(
            obj.submission.algorithm_image, context=self.context
        ).data


class ExternalEvaluationUpdateSerializer(EvaluationSerializer):
    outputs = ComponentInterfaceValuePostSerializer(many=True)

    class Meta:
        model = Evaluation
        fields = ("outputs", "status", "error_message")
