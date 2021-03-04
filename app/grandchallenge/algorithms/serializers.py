from typing import Optional

from rest_framework import serializers
from rest_framework.fields import CharField, SerializerMethodField
from rest_framework.relations import (
    HyperlinkedRelatedField,
    StringRelatedField,
)

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    Job,
)
from grandchallenge.components.serializers import (
    ComponentInterfaceValueSerializer,
    HyperlinkedComponentInterfaceValueSerializer,
)


class AlgorithmSerializer(serializers.ModelSerializer):
    algorithm_container_images = HyperlinkedRelatedField(
        many=True, read_only=True, view_name="api:algorithms-image-detail"
    )
    latest_ready_image = SerializerMethodField()
    average_duration = SerializerMethodField()

    class Meta:
        model = Algorithm
        fields = [
            "algorithm_container_images",
            "api_url",
            "description",
            "latest_ready_image",
            "pk",
            "title",
            "slug",
            "average_duration",
        ]

    def get_latest_ready_image(self, obj: Algorithm):
        """Used by latest_container_image SerializerMethodField."""
        ci = obj.latest_ready_image
        if ci:
            return ci.api_url
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
