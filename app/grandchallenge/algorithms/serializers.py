from typing import Optional

from rest_framework import serializers
from rest_framework.fields import (
    CharField,
    SerializerMethodField,
    SlugField,
    URLField,
)
from rest_framework.relations import (
    HyperlinkedRelatedField,
    StringRelatedField,
)

from grandchallenge.algorithms.models import Algorithm, AlgorithmImage, Job
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.components.serializers import (
    ComponentInterfaceSerializer,
    ComponentInterfaceValuePostSerializer,
    ComponentInterfaceValueSerializer,
    HyperlinkedComponentInterfaceValueSerializer,
)


class AlgorithmSerializer(serializers.ModelSerializer):
    average_duration = SerializerMethodField()
    inputs = ComponentInterfaceSerializer(many=True)
    outputs = ComponentInterfaceSerializer(many=True)
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

    def get_average_duration(self, obj: Algorithm) -> Optional[float]:
        """The average duration of successful jobs in seconds"""
        if obj.average_duration is None:
            return None
        else:
            return obj.average_duration.total_seconds()


class AlgorithmImageSerializer(serializers.ModelSerializer):
    algorithm = HyperlinkedRelatedField(
        read_only=True, view_name="api:algorithm-detail"
    )

    class Meta:
        model = AlgorithmImage
        fields = ["pk", "api_url", "algorithm"]


class JobSerializer(serializers.ModelSerializer):
    """Serializer without hyperlinks for internal use"""

    algorithm_image = StringRelatedField()
    inputs = ComponentInterfaceValueSerializer(many=True)
    outputs = ComponentInterfaceValueSerializer(many=True)

    status = CharField(source="get_status_display", read_only=True)
    algorithm_title = CharField(
        source="algorithm_image.algorithm.title", read_only=True
    )

    class Meta:
        model = Job
        fields = [
            "pk",
            "api_url",
            "algorithm_image",
            "inputs",
            "outputs",
            "status",
            "rendered_result_text",
            "algorithm_title",
            "started_at",
            "completed_at",
        ]


class HyperlinkedJobSerializer(JobSerializer):
    """Serializer with hyperlinks for use in public API"""

    algorithm_image = HyperlinkedRelatedField(
        queryset=AlgorithmImage.objects.all(),
        view_name="api:algorithms-image-detail",
    )
    inputs = HyperlinkedComponentInterfaceValueSerializer(many=True)
    outputs = HyperlinkedComponentInterfaceValueSerializer(many=True)

    class Meta(JobSerializer.Meta):
        pass


class JobPostSerializer(JobSerializer):
    algorithm_slug = SlugField(write_only=True)
    inputs = ComponentInterfaceValuePostSerializer(many=True)

    class Meta:
        model = Job
        fields = ["pk", "algorithm_slug", "inputs", "status"]

    def validate(self, data):
        alg = Algorithm.objects.get(slug=data.pop("algorithm_slug"))
        user = self.context.get("request").user

        if not user.has_perm("execute_algorithm", alg):
            raise serializers.ValidationError(
                f"User does not have permission to use algorithm {alg}"
            )

        if not alg.latest_ready_image:
            raise serializers.ValidationError(
                "Algorithm image is not ready to be used"
            )

        data["algorithm_image"] = alg.latest_ready_image

        # validate that no inputs are provided that are not configured for the
        # algorithm and that all interfaces without defaults are provided
        algorithm_input_ids = {a.id for a in alg.inputs.all()}
        input_ids = {i["interface_id"] for i in data["inputs"]}

        # surplus inputs: provided but interfaces not configured for the algorithm
        surplus = ComponentInterface.objects.filter(
            id__in=list(input_ids - algorithm_input_ids)
        )
        if surplus:
            titles = ", ".join(ci.title for ci in surplus)
            raise serializers.ValidationError(
                f"Provided inputs(s) {titles} are not defined for this algorithm"
            )

        # missing inputs
        missing = alg.inputs.filter(
            id__in=list(algorithm_input_ids - input_ids),
            default_value__isnull=True,
        )
        if missing:
            titles = ", ".join(ci.title for ci in missing)
            raise serializers.ValidationError(
                f"Interface(s) {titles} do not have a default value and should be provided."
            )

        return data

    def create(self, validated_data):
        inputs_data = validated_data.pop("inputs")
        job = Job.objects.create(**validated_data)
        component_interface_values = []
        upload_pks = {}
        algorithm_input_ids = {
            a.id for a in job.algorithm_image.algorithm.inputs.all()
        }
        input_ids = {i["interface_id"] for i in inputs_data}

        for input_data in inputs_data:
            # check for upload_pk in input
            upload_pk = input_data.pop("upload_pk", None)
            civ = ComponentInterfaceValue.objects.create(**input_data)
            component_interface_values.append(civ)
            if upload_pk:
                upload_pks[civ.pk] = upload_pk

        # use interface defaults if no value was provided
        defaults = job.algorithm_image.algorithm.inputs.filter(
            id__in=list(algorithm_input_ids - input_ids),
            default_value__isnull=False,
        )

        for d in defaults:
            component_interface_values.append(
                ComponentInterfaceValue.objects.create(
                    interface_id=d.id, value=d.default_value
                )
            )

        job.inputs.add(*component_interface_values)
        job.save()
        job.run_job(upload_pks=upload_pks)
        return job
