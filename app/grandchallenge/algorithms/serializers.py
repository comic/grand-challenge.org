from rest_framework import serializers
from grandchallenge.algorithms.models import Algorithm, Job, Result


class AlgorithmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Algorithm
        fields = ["pk", "slug", "title", "api_url"]


class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = ["pk", "job", "images", "output", "api_url"]


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ["pk", "algorithm", "image", "api_url"]
