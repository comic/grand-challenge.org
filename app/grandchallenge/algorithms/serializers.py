from rest_framework import serializers
from grandchallenge.algorithms.models import Algorithm, Job, Result


class AlgorithmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Algorithm
        fields = ['pk']


class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = ['pk', 'job', 'images', 'output']


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['pk', 'algorithm', 'image']
