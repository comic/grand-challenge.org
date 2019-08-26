from rest_framework import serializers
from rest_framework.relations import HyperlinkedRelatedField

from grandchallenge.algorithms.models import AlgorithmImage, Job, Result
from grandchallenge.cases.models import Image


class AlgorithmImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlgorithmImage
        fields = ["pk", "slug", "title", "api_url"]


class ResultSerializer(serializers.ModelSerializer):
    job = HyperlinkedRelatedField(
        read_only=True, view_name="api:algorithms-job-detail"
    )
    images = HyperlinkedRelatedField(
        many=True, read_only=True, view_name="api:image-detail"
    )

    class Meta:
        model = Result
        fields = ["pk", "job", "images", "output", "api_url"]


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
        fields = ["pk", "algorithm_image", "image", "api_url"]
