from functools import partial

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from drf_spectacular.utils import extend_schema_field
from guardian.core import ObjectPermissionChecker
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
from grandchallenge.evaluation.templatetags.evaluation_extras import (
    get_jsonpath,
)


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


class FilteredMetricsJsonSerializer(ComponentInterfaceValueSerializer):
    value = SerializerMethodField(method_name="filtered_metrics_json")

    def __init__(self, *args, filter_metrics_json, valid_metrics, **kwargs):
        super().__init__(*args, **kwargs)
        self.filter_metrics_json = filter_metrics_json
        self.valid_metrics = valid_metrics

    def filtered_metrics_json(self, obj):
        if (
            obj.interface.slug == "metrics-json-file"
            and self.filter_metrics_json
        ):
            output = {}

            for metric in self.valid_metrics:
                value = get_jsonpath(obj.value, metric.path)

                if not isinstance(value, (int, float)):
                    continue

                keys = str(metric.path).split(".")

                sub_output = output

                for key in keys[:-1]:
                    if key not in sub_output:
                        sub_output[key] = {}
                    sub_output = sub_output[key]

                sub_output[keys[-1]] = value

            return output
        else:
            return obj.value


class EvaluationSerializer(ModelSerializer):
    submission = SubmissionSerializer()
    outputs = SerializerMethodField()
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        challenge_permission_checker = ObjectPermissionChecker(
            user_or_group=self.context["request"].user
        )
        challenge_permission_checker.prefetch_perms(
            objects=Challenge.objects.all()
        )
        self._challenge_permission_checker = challenge_permission_checker

    @extend_schema_field(ComponentInterfaceValueSerializer(many=True))
    def get_outputs(self, obj):
        return_all_metrics = (
            obj.submission.phase.display_all_metrics
            or "change_challenge"
            in self._challenge_permission_checker.get_perms(
                obj.submission.phase.challenge
            )
        )

        if return_all_metrics:
            serializer = ComponentInterfaceValueSerializer
        else:
            serializer = partial(
                FilteredMetricsJsonSerializer,
                filter_metrics_json=True,
                valid_metrics=obj.submission.phase.valid_metrics,
            )

        return serializer(
            obj.outputs.all(),
            many=True,
            context=self.context,
        ).data


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
        validated_data["claimed_at"] = now()
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

        if data["status"] == Evaluation.SUCCESS:
            interface = ComponentInterface.objects.get(
                slug="metrics-json-file"
            )
            civ = ComponentInterfaceValue(
                interface=interface, value=data["metrics"]
            )
            try:
                civ.full_clean()
                civ.save()
                self.instance.outputs.add(civ)
            except ValidationError as e:
                raise DRFValidationError(e)

        return data

    def update(self, instance, validated_data):
        extra_kwargs = {}
        status = validated_data["status"]
        if (
            status
            in [
                Evaluation.EXECUTED,
                Evaluation.SUCCESS,
                Evaluation.FAILURE,
                Evaluation.CANCELLED,
            ]
            and instance.evaluation_utilization.duration is None
        ):
            extra_kwargs["utilization_duration"] = now() - instance.claimed_at

        # calling update_status takes care of sending the notifications
        instance.update_status(
            status=validated_data["status"],
            error_message=(
                validated_data["error_message"]
                if "error_message" in validated_data.keys()
                else None
            ),
            compute_cost_euro_millicents=0,
            **extra_kwargs,
        )
        return super().update(instance, validated_data)
