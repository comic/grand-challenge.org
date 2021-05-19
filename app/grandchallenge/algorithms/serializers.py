from typing import Optional

from rest_framework import serializers
from rest_framework.fields import CharField, SerializerMethodField
from rest_framework.relations import (
    HyperlinkedRelatedField,
    StringRelatedField,
)

from grandchallenge.algorithms.models import Algorithm, AlgorithmImage, Job
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.components.serializers import (
    ComponentInterfaceSerializer,
    ComponentInterfaceValuePostSerializer,
    ComponentInterfaceValueSerializer,
    HyperlinkedComponentInterfaceValueSerializer,
)


class AlgorithmSerializer(serializers.ModelSerializer):
    average_duration = SerializerMethodField()
    inputs = ComponentInterfaceSerializer(many=True)
    latest_ready_image = SerializerMethodField()

    class Meta:
        model = Algorithm
        fields = [
            "api_url",
            "description",
            "pk",
            "title",
            "slug",
            "average_duration",
            "inputs",
            "latest_ready_image",
        ]

    def get_latest_ready_image(self, obj: Algorithm):
        """Used by latest_container_image SerializerMethodField."""
        ci = obj.latest_ready_image
        if ci:
            return ci.pk
        else:
            return None

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
    algorithm_title = CharField(write_only=True)
    inputs = ComponentInterfaceValuePostSerializer(many=True)

    class Meta:
        model = Job
        fields = ["pk", "algorithm_title", "inputs", "status"]

    def validate(self, data):
        alg = Algorithm.objects.get(title=data.pop("algorithm_title"))
        if not alg.latest_ready_image:
            raise serializers.ValidationError("Algorithm image is not ready to be used")

        data["algorithm_image"] = alg.latest_ready_image
        return data

    def create(self, validated_data):
        inputs_data = validated_data.pop("inputs")
        job = Job.objects.create(**validated_data)
        component_interface_values = []
        upload_pks = {}
        algorithm_inputs = job.algorithm_image.algorithm.inputs.all()
        for input_data in inputs_data:
            # check for upload_pk in input
            upload_pk = input_data.pop("upload_pk", None)
            civ = ComponentInterfaceValue.objects.create(**input_data)
            component_interface_values.append(civ)
            if upload_pk:
                upload_pks[civ.pk] = str(upload_pk)

        # use interface defaults if no value was provided
        for input_interface in algorithm_inputs:
            if input_interface.default_value is not None and input_interface.id not in (
                input_data["interface_id"] for input_data in inputs_data
            ):
                component_interface_values.append(
                    ComponentInterfaceValue.objects.create(
                        interface_id=input_interface.id,
                        value=input_interface.default_value,
                    )
                )

        job.inputs.add(*component_interface_values)
        job.save()
        job.run_job(upload_pks=upload_pks)
        return job
