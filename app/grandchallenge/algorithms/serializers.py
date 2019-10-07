from rest_framework import serializers
from rest_framework.relations import HyperlinkedRelatedField

from grandchallenge.algorithms.models import (
    AlgorithmImage,
    Job,
    Result,
    Algorithm,
)
from grandchallenge.cases.models import Image


class AlgorithmSerializer(serializers.ModelSerializer):
    algorithmimage_set = HyperlinkedRelatedField(
        many=True, read_only=True, view_name="api:algorithm-image-detail"
    )

    class Meta:
        model = Algorithm
        fields = [
            "pk",
            "api_url",
            "title",
            "description",
            "algorithmimage_set",
        ]


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
