from django.core.exceptions import ValidationError
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

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmModel,
    Job,
)
from grandchallenge.components.models import CIVData, ComponentInterface
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
            "image",
        ]


class AlgorithmModelSerializer(serializers.ModelSerializer):
    algorithm = HyperlinkedRelatedField(
        read_only=True, view_name="api:algorithm-detail"
    )
    import_status = CharField(
        source="get_import_status_display", read_only=True
    )

    class Meta:
        model = AlgorithmModel
        fields = ["pk", "algorithm", "created", "import_status", "model"]


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
        non_interface_fields = [
            "algorithm_image",
            "algorithm_model",
            "creator",
            "time_limit",
        ]

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
        data["time_limit"] = self._algorithm.time_limit

        jobs_limit = data["algorithm_image"].get_remaining_jobs(
            user=data["creator"]
        )
        if jobs_limit < 1:
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

        inputs = data.pop("inputs")

        default_inputs = self._algorithm.inputs.filter(
            id__in=list(algorithm_input_pks - input_pks),
            default_value__isnull=False,
        )
        # Use default interface values if not present
        for interface in default_inputs:
            if interface.default_value:
                inputs.append(
                    {"interface": interface, "value": interface.default_value}
                )

        self.inputs = self.reformat_inputs(serialized_civs=inputs)

        if Job.objects.get_jobs_with_same_inputs(
            inputs=self.inputs,
            algorithm_image=data["algorithm_image"],
            algorithm_model=data["algorithm_model"],
        ):
            raise serializers.ValidationError(
                "A result for these inputs with the current image "
                "and model already exists."
            )

        return data

    def create(self, validated_data):
        job = Job.objects.create(
            **validated_data,
            extra_logs_viewer_groups=[
                validated_data["algorithm_image"].algorithm.editors_group
            ],
            status=Job.VALIDATING_INPUTS,
        )
        job.create_and_validate_inputs(inputs=self.inputs)
        return job

    @staticmethod
    def reformat_inputs(*, serialized_civs):
        """Takes serialized CIV data and returns list of CIVData objects."""
        possible_keys = [
            "image",
            "value",
            "file",
            "user_upload",
            "upload_session",
        ]

        data = []
        for civ in serialized_civs:
            found_keys = [key for key in possible_keys if key in civ]

            if not found_keys:
                raise serializers.ValidationError(
                    f"You must provide at least one of {possible_keys}"
                )

            if len(found_keys) > 1:
                raise serializers.ValidationError(
                    f"You can only provide one of {possible_keys} for each interface."
                )

            try:
                data.append(
                    CIVData(
                        interface_slug=civ["interface"].slug,
                        value=civ[found_keys[0]],
                    )
                )
            except ValidationError as e:
                raise serializers.ValidationError(e)

        return data
