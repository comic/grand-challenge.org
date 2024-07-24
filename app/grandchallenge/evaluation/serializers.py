from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.fields import (
    CharField,
    ChoiceField,
    JSONField,
    SerializerMethodField,
)
from rest_framework.relations import HyperlinkedRelatedField
from rest_framework.serializers import ModelSerializer

from grandchallenge.algorithms.serializers import (
    AlgorithmImageSerializer,
    AlgorithmModelSerializer,
)
from grandchallenge.challenges.models import Challenge
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.components.serializers import (
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
            "claimed_by",
        )

    def get_algorithm_model(self, obj) -> dict | None:
        if obj.submission.algorithm_model:
            return AlgorithmModelSerializer(
                obj.submission.algorithm_model, context=self.context
            ).data
        return None

    def get_algorithm_image(self, obj) -> dict:
        return AlgorithmImageSerializer(
            obj.submission.algorithm_image, context=self.context
        ).data

    def update(self, instance, validated_data):
        validated_data["claimed_by"] = self.context["request"].user
        validated_data["started_at"] = now()
        validated_data["status"] = Evaluation.CLAIMED
        return super().update(instance, validated_data)


class ExternalEvaluationStatusField(ChoiceField):
    def __init__(self, *args, **kwargs):
        self.external_to_internal_status_mapping = {
            "Succeeded": Evaluation.SUCCESS,
            "Failed": Evaluation.FAILURE,
        }
        self.internal_to_external_status_mapping = {
            v: k for k, v in self.external_to_internal_status_mapping.items()
        }
        choices = list(self.external_to_internal_status_mapping.keys())
        super().__init__(*args, choices=choices, **kwargs)

    def to_internal_value(self, data):
        # Convert the external value to the internal value
        if data in self.external_to_internal_status_mapping:
            return self.external_to_internal_status_mapping[data]
        self.fail("invalid_choice", input=data)

    def to_representation(self, value):
        # Convert the internal value to the external value for representation
        if value in self.internal_to_external_status_mapping:
            return self.internal_to_external_status_mapping[value]
        self.fail("invalid_choice", input=value)


class ExternalEvaluationUpdateSerializer(ModelSerializer):
    metrics = JSONField(required=False)
    status = ExternalEvaluationStatusField()

    class Meta:
        model = Evaluation
        fields = ("metrics", "status", "error_message")

    def validate(self, data):
        if data["status"] == Evaluation.SUCCESS and "metrics" not in data:
            raise DRFValidationError(
                "Metrics are required for successful evaluations."
            )
        if (
            data["status"] == Evaluation.FAILURE
            and "error_message" not in data
        ):
            raise DRFValidationError(
                "An error_message is required for failed evaluations."
            )
        return data

    def update(self, instance, validated_data):
        if validated_data["status"] == Evaluation.SUCCESS:
            interface = ComponentInterface.objects.get(
                slug="metrics-json-file"
            )
            civ = ComponentInterfaceValue(
                interface=interface, value=validated_data["metrics"]
            )
            try:
                civ.full_clean()
                civ.save()
                instance.outputs.add(civ)
            except ValidationError as e:
                raise DRFValidationError(e)
        validated_data["completed_at"] = now()
        validated_data["compute_cost_euro_millicents"] = 0
        return super().update(instance, validated_data)
