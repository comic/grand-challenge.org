import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
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
    AlgorithmInterface,
    AlgorithmModel,
    Job,
    annotate_input_output_counts,
)
from grandchallenge.cases.widgets import DICOMUploadWithName
from grandchallenge.components.backends.exceptions import (
    CIVNotEditableException,
)
from grandchallenge.components.models import CIVData
from grandchallenge.components.serializers import (
    ComponentInterfaceSerializer,
    ComponentInterfaceValuePostSerializer,
    ComponentInterfaceValueSerializer,
    HyperlinkedComponentInterfaceValueSerializer,
)
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
    logo = URLField(source="logo.x20.url", read_only=True)
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
            self.validate_inputs_and_return_matching_interface(inputs=inputs)
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
        algorithm = validated_data["algorithm_image"].algorithm

        job = Job.objects.create(
            **validated_data,
            time_limit=algorithm.time_limit,
            requires_gpu_type=algorithm.job_requires_gpu_type,
            requires_memory_gb=algorithm.job_requires_memory_gb,
            extra_logs_viewer_groups=[algorithm.editors_group],
            status=Job.VALIDATING_INPUTS,
        )

        try:
            job.validate_civ_data_objects_and_execute_linked_task(
                civ_data_objects=self.inputs, user=validated_data["creator"]
            )
        except CIVNotEditableException as e:
            if job.status == job.CANCELLED:
                # this can happen for jobs with multiple inputs
                # if one of them fails validation
                pass
            else:
                error_handler = job.get_error_handler()
                error_handler.handle_error(
                    error_message="An unexpected error occurred",
                )
                logger.error(e, exc_info=True)

        return job

    def validate_inputs_and_return_matching_interface(self, *, inputs):
        """
        Validates that the provided inputs match one of the configured interfaces of
        the algorithm and returns that AlgorithmInterface
        """
        provided_inputs = {i["interface"] for i in inputs}
        annotated_qs = annotate_input_output_counts(
            self._algorithm.interfaces, inputs=provided_inputs
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
                f"any of the algorithm's interfaces. This algorithm supports the "
                f"following input combinations: "
                f"{oxford_comma([f'Interface {n}: {oxford_comma(interface.inputs.all())}' for n, interface in enumerate(self._algorithm.interfaces.all(), start=1)])}"
            )

    @staticmethod
    def reformat_inputs(*, serialized_civs):
        """Takes serialized CIV data and returns list of CIVData objects."""

        data = []
        for civ in serialized_civs:
            interface = civ["interface"]
            upload_session = civ.get("upload_session")
            user_upload = civ.get("user_upload")
            image = civ.get("image")
            value = civ.get("value")
            user_uploads = civ.get("user_uploads")
            image_name = civ.get("image_name")
            dicom_upload_with_name = (
                DICOMUploadWithName(name=image_name, user_uploads=user_uploads)
                if user_uploads and image_name
                else None
            )
            try:
                data.append(
                    CIVData(
                        interface_slug=interface.slug,
                        value=upload_session
                        or user_upload
                        or image
                        or value
                        or dicom_upload_with_name,
                    )
                )
            except ValidationError as e:
                raise serializers.ValidationError(e)

        return data
