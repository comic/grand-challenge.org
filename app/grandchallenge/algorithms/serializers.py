from rest_framework import serializers
from rest_framework.relations import HyperlinkedRelatedField
from rest_framework.serializers import HyperlinkedModelSerializer

from grandchallenge.cases.models import Image
from grandchallenge.algorithms.models import Algorithm, Job, Result


class AlgorithmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Algorithm
        fields = ["pk", "slug", "title", "api_url"]


class ResultSerializer(serializers.ModelSerializer):
    job = HyperlinkedRelatedField(
        view_name="api:algorithms-job-detail", queryset=Job.objects.all()
    )

    class Meta:
        model = Result
        fields = ["pk", "job", "images", "output", "api_url"]


class JobSerializer(serializers.ModelSerializer):
    algorithm = HyperlinkedRelatedField(
        view_name="api:algorithm-detail", queryset=Algorithm.objects.all()
    )

    class Meta:
        model = Job
        fields = ["pk", "algorithm", "image", "api_url"]
