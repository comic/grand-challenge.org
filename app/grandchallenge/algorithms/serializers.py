from django.db import transaction
from rest_framework import serializers
from rest_framework.fields import (
    CharField,
    JSONField,
    SerializerMethodField,
    URLField,
)
from rest_framework.relations import (
    HyperlinkedRelatedField,
    StringRelatedField,
)

from grandchallenge.algorithms.models import Algorithm, AlgorithmImage, Job
from grandchallenge.components.models import ComponentInterface
from grandchallenge.components.serializers import (
    ComponentInterfaceSerializer,
    ComponentInterfaceValuePostSerializer,
    ComponentInterfaceValueSerializer,
    HyperlinkedComponentInterfaceValueSerializer,
)
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.hanging_protocols.serializers import (
    HangingProtocolSerializer,
)


class AlgorithmSerializer(serializers.ModelSerializer):
    average_duration = SerializerMethodField()
    inputs = ComponentInterfaceSerializer(many=True, read_only=True)
    outputs = ComponentInterfaceSerializer(many=True, read_only=True)
    logo = URLField(source="logo.x20.url", read_only=True)
    url = URLField(source="get_absolute_url", read_only=True)

    class Meta:
        model = Algorithm
        fields = [
            "api_url",
            "url",
            "description",
            "pk",
            "title",
            "logo",
            "slug",
            "average_duration",
            "inputs",
            "outputs",
        ]

    def get_average_duration(self, obj: Algorithm) -> float | None:
        """The average duration of successful jobs in seconds"""
        if obj.average_duration is None:
            return None
        else:
            return obj.average_duration.total_seconds()


class AlgorithmImageSerializer(serializers.ModelSerializer):
    algorithm = HyperlinkedRelatedField(
        read_only=True, view_name="api:algorithm-detail"
    )
    url = URLField(source="get_absolute_url", read_only=True)
    import_status = CharField(
        source="get_import_status_display", read_only=True
    )

    class Meta:
        model = AlgorithmImage
        fields = [
            "pk",
            "url",
            "api_url",
            "algorithm",
            "created",
            "requires_gpu",
            "requires_memory_gb",
            "import_status",
        ]


class JobSerializer(serializers.ModelSerializer):
    """Serializer without hyperlinks for internal use"""

    algorithm_image = StringRelatedField()

    inputs = ComponentInterfaceValueSerializer(many=True)
    outputs = ComponentInterfaceValueSerializer(many=True)

    status = CharField(source="get_status_display", read_only=True)
    url = URLField(source="get_absolute_url", read_only=True)
    hanging_protocol = HangingProtocolSerializer(
        source="algorithm_image.algorithm.hanging_protocol",
        read_only=True,
        allow_null=True,
    )
    optional_hanging_protocols = HangingProtocolSerializer(
        many=True,
        source="algorithm_image.algorithm.optional_hanging_protocols",
        read_only=True,
        required=False,
    )
    view_content = JSONField(
        source="algorithm_image.algorithm.view_content", read_only=True
    )

    class Meta:
        model = Job
        fields = [
            "pk",
            "url",
            "api_url",
            "algorithm_image",
            "inputs",
            "outputs",
            "status",
            "rendered_result_text",
            "started_at",
            "completed_at",
            "hanging_protocol",
            "optional_hanging_protocols",
            "view_content",
        ]


class HyperlinkedJobSerializer(JobSerializer):
    """Serializer with hyperlinks for use in public API"""

    algorithm_image = HyperlinkedRelatedField(
        queryset=AlgorithmImage.objects.all(),
        view_name="api:algorithms-image-detail",
    )
    algorithm = HyperlinkedRelatedField(
        source="algorithm_image.algorithm",
        view_name="api:algorithm-detail",
        read_only=True,
    )

    inputs = HyperlinkedComponentInterfaceValueSerializer(many=True)
    outputs = HyperlinkedComponentInterfaceValueSerializer(many=True)

    class Meta(JobSerializer.Meta):
        fields = [
            *JobSerializer.Meta.fields,
            "algorithm",
        ]


class JobPostSerializer(JobSerializer):
    algorithm = HyperlinkedRelatedField(
        queryset=Algorithm.objects.none(),
        view_name="api:algorithm-detail",
        write_only=True,
    )

    class Meta:
        model = Job
        fields = ["pk", "algorithm", "inputs", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["inputs"] = ComponentInterfaceValuePostSerializer(
            many=True, context=self.context
        )

        if "request" in self.context:
            user = self.context["request"].user

            self.fields["algorithm"].queryset = filter_by_permission(
                queryset=Algorithm.objects.all(),
                user=user,
                codename="execute_algorithm",
            )

    @transaction.atomic
    def validate(self, data):
        self._algorithm = data.pop("algorithm")
        user = self.context["request"].user

        if not self._algorithm.active_image:
            raise serializers.ValidationError(
                "Algorithm image is not ready to be used"
            )
        data["creator"] = user
        data["algorithm_image"] = self._algorithm.active_image
        data["algorithm_model"] = self._algorithm.active_model

        jobs_limit = self._algorithm.active_image.algorithm.get_jobs_limit(
            user=data["creator"]
        )
        if jobs_limit is not None and jobs_limit < 1:
            raise serializers.ValidationError(
                "You have run out of algorithm credits"
            )

        # validate that no inputs are provided that are not configured for the
        # algorithm and that all interfaces without defaults are provided
        algorithm_input_pks = {a.pk for a in self._algorithm.inputs.all()}
        input_pks = {i["interface"].pk for i in data["inputs"]}

        # surplus inputs: provided but interfaces not configured for the algorithm
        surplus = ComponentInterface.objects.filter(
            id__in=list(input_pks - algorithm_input_pks)
        )
        if surplus:
            titles = ", ".join(ci.title for ci in surplus)
            raise serializers.ValidationError(
                f"Provided inputs(s) {titles} are not defined for this algorithm"
            )

        # missing inputs
        missing = self._algorithm.inputs.filter(
            id__in=list(algorithm_input_pks - input_pks),
            default_value__isnull=True,
        )
        if missing:
            titles = ", ".join(ci.title for ci in missing)
            raise serializers.ValidationError(
                f"Interface(s) {titles} do not have a default value and should be provided."
            )

        validated_data = super().validate()
        job = Job.objects.create_and_process_inputs(
            user=user,
            algorithm=self._algorithm,
            data=validated_data,
            extra_logs_viewer_groups=[
                validated_data["algorithm_image"].algorithm.editors_group
            ],
        )

        if job.get_jobs_with_same_inputs():
            raise serializers.ValidationError(
                "A result for these inputs with the current image "
                "and model already exists."
            )

        data["job"] = job

        return data

    def create(self, validated_data):
        # Job creation takes place during validation because we need the job there to
        # check if the job has been run yet
        return validated_data["job"]
