import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from rest_framework import serializers
from rest_framework.fields import (
    CharField,
    DurationField,
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
    AlgorithmInterface,
    AlgorithmModel,
    Endpoint,
    Invocation,
    InvocationStatusChoices,
    Job,
    annotate_input_output_counts,
)
from grandchallenge.components.backends.exceptions import (
    CIVNotEditableException,
)
from grandchallenge.components.models import APIMethodChoices
from grandchallenge.components.serializers import (
    ComponentInterfaceSerializer,
    ComponentInterfaceValuePostSerializer,
    ComponentInterfaceValueSerializer,
    HyperlinkedComponentInterfaceValueSerializer,
    convert_deserialized_civ_data,
)
from grandchallenge.core.error_messages import SystemErrorMessages
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.hanging_protocols.serializers import (
    HangingProtocolSerializer,
)

logger = logging.getLogger(__name__)


class AlgorithmInterfaceSerializer(serializers.ModelSerializer):
    """Serializer without hyperlinks for internal use"""

    inputs = ComponentInterfaceSerializer(many=True, read_only=True)
    outputs = ComponentInterfaceSerializer(many=True, read_only=True)

    class Meta:
        model = AlgorithmInterface
        fields = [
            "inputs",
            "outputs",
        ]


class AlgorithmSerializer(serializers.ModelSerializer):
    average_duration = SerializerMethodField()
    url = URLField(source="get_absolute_url", read_only=True)
    interfaces = AlgorithmInterfaceSerializer(many=True, read_only=True)

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
            "interfaces",
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


class EndpointSerializer(serializers.ModelSerializer):
    algorithm = HyperlinkedRelatedField(
        source="algorithm_image.algorithm",
        view_name="api:algorithm-detail",
        read_only=True,
    )
    status = CharField(source="get_status_display", read_only=True)
    remaining_lifetime = DurationField(
        source="get_remaining_lifetime",
        read_only=True,
    )

    class Meta:
        model = Endpoint
        fields = [
            "api_url",
            "pk",
            "algorithm",
            "status",
            "remaining_lifetime",
        ]


class EndpointPostSerializer(EndpointSerializer):
    algorithm = HyperlinkedRelatedField(
        source="algorithm_image.algorithm",
        queryset=Algorithm.objects.none(),
        view_name="api:algorithm-detail",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "request" in self.context:
            user = self.context["request"].user

            self.fields["algorithm"].queryset = filter_by_permission(
                queryset=Algorithm.objects.all(),
                user=user,
                codename="execute_algorithm",
            )

    def validate(self, data):
        algorithm = data["algorithm_image"]["algorithm"]
        user = self.context["request"].user

        if not algorithm.active_image:
            raise serializers.ValidationError(
                "Algorithm image is not ready to be used"
            )

        if not algorithm.active_image.api_method == APIMethodChoices.INVOKE:
            raise serializers.ValidationError(
                "Algorithm image does not implement the invoke API"
            )

        try:
            remaining_credits = AlgorithmImage.get_remaining_specific_credits(
                user=user, algorithm=algorithm
            )
        except ObjectDoesNotExist:
            remaining_credits = 0

        if remaining_credits <= 0:
            raise serializers.ValidationError(
                "You have run out of algorithm credits"
            )

        if (
            Endpoint.objects.active()
            .filter(creator=user, algorithm_image__algorithm=algorithm)
            .count()
            > 0
        ):
            raise ValidationError(
                "You already have an active endpoint for this algorithm"
            )

        if (
            Endpoint.objects.active().filter(creator=user).count()
            >= settings.ALGORITHM_ENDPOINTS_MAX_ACTIVE_ENDPOINTS_PER_USER
        ):
            raise ValidationError("You have too many active endpoints")

        data["creator"] = user
        data["algorithm_image"] = algorithm.active_image
        data["algorithm_model"] = algorithm.active_model
        data["requires_gpu_type"] = algorithm.job_requires_gpu_type
        data["requires_memory_gb"] = algorithm.job_requires_memory_gb

        return data


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
            "hanging_protocol",
            "optional_hanging_protocols",
            "view_content",
            "exec_duration",
            "invoke_duration",
        ]


def validate_inputs_and_return_matching_interface(
    *, inputs, allowed_algorithm_interfaces
):
    """
    Validates that the provided inputs match one of the allowed algorithm interfaces and returns the interface.
    """
    provided_inputs = {i["interface"] for i in inputs}
    annotated_qs = annotate_input_output_counts(
        allowed_algorithm_interfaces, inputs=provided_inputs
    )
    try:
        interface = annotated_qs.get(
            relevant_input_count=len(provided_inputs),
            input_count=len(provided_inputs),
        )
        return interface
    except ObjectDoesNotExist:
        raise serializers.ValidationError(
            f"The set of inputs provided does not match "
            f"any of the allowed algorithm interfaces. The "
            f"following input combinations are allowed: "
            f"{oxford_comma([f'Interface {n}: {oxford_comma(interface.inputs.all())}' for n, interface in enumerate(allowed_algorithm_interfaces, start=1)])}"
        )


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

    def validate(self, data):
        algorithm = data.pop("algorithm")
        user = self.context["request"].user

        if not algorithm.active_image:
            raise serializers.ValidationError(
                "Algorithm image is not ready to be used"
            )
        data["creator"] = user
        data["algorithm_image"] = algorithm.active_image
        data["algorithm_model"] = algorithm.active_model

        jobs_limit = data["algorithm_image"].get_remaining_jobs(
            user=data["creator"]
        )
        if jobs_limit < 1:
            raise serializers.ValidationError(
                "You have run out of algorithm credits"
            )

        if (
            Job.objects.active().filter(creator=data["creator"]).count()
            >= settings.ALGORITHMS_MAX_ACTIVE_JOBS_PER_USER
        ):
            raise ValidationError(
                "You have too many active jobs, "
                "please try again after they have completed"
            )

        inputs = data.pop("inputs")
        data["algorithm_interface"] = (
            validate_inputs_and_return_matching_interface(
                inputs=inputs,
                allowed_algorithm_interfaces=algorithm.interfaces.all(),
            )
        )
        data["civ_data_objects"] = convert_deserialized_civ_data(
            deserialized_civ_data=inputs
        )

        if Job.objects.get_jobs_with_same_inputs(
            inputs=data["civ_data_objects"],
            algorithm_image=data["algorithm_image"],
            algorithm_model=data["algorithm_model"],
        ):
            raise serializers.ValidationError(
                "A result for these inputs with the current image "
                "and model already exists."
            )

        return data

    def create(self, validated_data):
        algorithm = validated_data["algorithm_image"].algorithm
        civ_data_objects = validated_data.pop("civ_data_objects", [])

        job = Job.objects.create(
            **validated_data,
            time_limit=algorithm.time_limit,
            requires_gpu_type=algorithm.job_requires_gpu_type,
            requires_memory_gb=algorithm.job_requires_memory_gb,
            extra_logs_viewer_groups=[algorithm.editors_group],
            status=Job.VALIDATING_INPUTS,
        )

        try:
            job.process_civ_data_objects_and_execute_linked_task(
                civ_data_objects=civ_data_objects,
                user=validated_data["creator"],
            )
        except CIVNotEditableException as e:
            if job.status == job.CANCELLED:
                # this can happen for jobs with multiple inputs
                # if one of them fails validation
                pass
            else:
                error_handler = job.get_error_handler()
                error_handler.handle_error(
                    error_message=SystemErrorMessages.UNEXPECTED_ERROR,
                )
                logger.error(e, exc_info=True)

        return job


class InvocationSerializer(serializers.ModelSerializer):
    """Serializer with hyperlinks for use in public API"""

    endpoint = HyperlinkedRelatedField(
        queryset=Endpoint.objects.none(),
        view_name="api:algorithms-endpoint-detail",
        required=True,
    )
    inputs = HyperlinkedComponentInterfaceValueSerializer(many=True)
    outputs = HyperlinkedComponentInterfaceValueSerializer(many=True)
    status = CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Invocation
        fields = [
            "pk",
            "endpoint",
            "inputs",
            "outputs",
            "status",
            "error_message",
        ]


class InvocationPostSerializer(serializers.ModelSerializer):

    endpoint = HyperlinkedRelatedField(
        queryset=Endpoint.objects.none(),
        view_name="api:algorithms-endpoint-detail",
        required=True,
    )
    status = CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Invocation
        fields = ["pk", "endpoint", "inputs", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["inputs"] = ComponentInterfaceValuePostSerializer(
            many=True, context=self.context
        )

        if "request" in self.context:
            user = self.context["request"].user

            self.fields["endpoint"].queryset = filter_by_permission(
                queryset=Endpoint.objects.filter(
                    status=Endpoint.StatusChoices.RUNNING
                ),
                user=user,
                codename="invoke_endpoint",
            )

    def validate(self, data):
        endpoint = data["endpoint"]

        if (
            Invocation.objects.active().filter(endpoint=endpoint).count()
            >= settings.ALGORITHM_ENDPOINTS_MAX_ACTIVE_INVOCATIONS_PER_ENDPOINT
        ):
            raise ValidationError(
                "There are too many active invocations for this endpoint, "
                "please try again after they have completed"
            )

        inputs = data.pop("inputs")
        data["algorithm_interface"] = (
            validate_inputs_and_return_matching_interface(
                inputs=inputs,
                allowed_algorithm_interfaces=endpoint.algorithm_image.algorithm.interfaces.all(),
            )
        )
        data["civ_data_objects"] = convert_deserialized_civ_data(
            deserialized_civ_data=inputs
        )

        return data

    def create(self, validated_data):
        civ_data_objects = validated_data.pop("civ_data_objects", [])

        invocation = Invocation.objects.create(
            **validated_data,
            time_limit=settings.ALGORITHM_ENDPOINTS_MAXIMUM_INVOCATION_DURATION,
            status=InvocationStatusChoices.VALIDATING_INPUTS,
        )

        try:
            invocation.process_civ_data_objects_and_execute_linked_task(
                civ_data_objects=civ_data_objects,
                user=self.context["request"].user,
            )
        except CIVNotEditableException as e:
            invocation.refresh_from_db()
            if invocation.status == invocation.StatusChoices.CANCELLED:
                # this can happen for jobs with multiple inputs
                # if one of them fails validation
                pass
            else:
                error_handler = invocation.get_error_handler()
                error_handler.handle_error(
                    error_message=SystemErrorMessages.UNEXPECTED_ERROR,
                )
                logger.error(e, exc_info=True)

        if not invocation.endpoint.is_linked_to_reader_study:
            invocation.endpoint.keep_alive(
                duration=invocation.orchestrator.invocation_time_limit
            )

        return invocation
