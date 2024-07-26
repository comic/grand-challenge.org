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
    phase_pk = CharField(source="submission.phase.pk")

    class Meta:
        model = Evaluation
        fields = (
            *EvaluationSerializer.Meta.fields,
            "algorithm_model",
            "algorithm_image",
            "claimed_by",
            "phase_pk",
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
    external_to_internal_status_mapping = {
        "Succeeded": Evaluation.SUCCESS,
        "Failed": Evaluation.FAILURE,
    }

    def __init__(self, *args, **kwargs):
        choices = list(self.external_to_internal_status_mapping.keys())
        super().__init__(*args, choices=choices, **kwargs)

    def to_internal_value(self, data):
        if data in self.external_to_internal_status_mapping:
            return self.external_to_internal_status_mapping[data]
        raise DRFValidationError("Not a valid choice.")

    def to_representation(self, value):
        for (
            external_value,
            internal_value,
        ) in self.external_to_internal_status_mapping.items():
            if value == internal_value:
                return external_value
        raise DRFValidationError("Not a valid choice.")


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

        # calling update_status takes care of sending the notifications
        instance.update_status(
            status=validated_data["status"],
            error_message=validated_data["error_message"],
            compute_cost_euro_millicents=0,
        )

        return super().update(instance, validated_data)
