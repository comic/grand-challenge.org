from rest_framework import serializers
from rest_framework.relations import HyperlinkedRelatedField, SlugRelatedField

from grandchallenge.algorithms.models import Algorithm, Job, Result
from grandchallenge.cases.models import Image


class AlgorithmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Algorithm
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
    creator = SlugRelatedField(read_only=True, slug_field="username")
    algorithm = HyperlinkedRelatedField(
        read_only=True, view_name="api:algorithm-detail"
    )
    image = HyperlinkedRelatedField(
        many=True, queryset=Image.objects.all(), view_name="api:image-detail"
    )

    class Meta:
        model = Job
        fields = ["pk", "algorithm", "image", "api_url", "creator"]
