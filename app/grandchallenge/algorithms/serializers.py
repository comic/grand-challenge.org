from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.relations import HyperlinkedRelatedField

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    Job,
    Result,
)
from grandchallenge.cases.models import Image


class AlgorithmSerializer(serializers.ModelSerializer):
    algorithm_container_images = HyperlinkedRelatedField(
        many=True, read_only=True, view_name="api:algorithms-image-detail"
    )
    latest_ready_image = SerializerMethodField()

    class Meta:
        model = Algorithm
        fields = [
            "algorithm_container_images",
            "api_url",
            "description",
            "latest_ready_image",
            "pk",
            "title",
        ]

    def get_latest_ready_image(self, obj: Algorithm):
        """Used by latest_container_image SerializerMethodField."""
        ci = obj.latest_ready_image
        if ci:
            return ci.api_url
        else:
            return None


class AlgorithmImageSerializer(serializers.ModelSerializer):
    algorithm = HyperlinkedRelatedField(
        read_only=True, view_name="api:algorithm-detail"
    )

    class Meta:
        model = AlgorithmImage
        fields = ["pk", "api_url", "algorithm"]


class ResultSerializer(serializers.ModelSerializer):
    job = HyperlinkedRelatedField(
        read_only=True, view_name="api:algorithms-job-detail"
    )
    images = HyperlinkedRelatedField(
        many=True, read_only=True, view_name="api:image-detail"
    )

    class Meta:
        model = Result
        fields = ["pk", "api_url", "job", "images", "output"]


class JobSerializer(serializers.ModelSerializer):
    algorithm_image = HyperlinkedRelatedField(
        queryset=AlgorithmImage.objects.all(),
        view_name="api:algorithms-image-detail",
    )
    image = HyperlinkedRelatedField(
        queryset=Image.objects.all(), view_name="api:image-detail"
    )

    class Meta:
        model = Job
        fields = ["pk", "api_url", "algorithm_image", "image"]
