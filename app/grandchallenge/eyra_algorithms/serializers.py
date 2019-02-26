from rest_framework import serializers

from grandchallenge.eyra_algorithms.models import Algorithm, Job, Interface


class AlgorithmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Algorithm
        fields = '__all__'


class InterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interface
        fields = '__all__'


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = '__all__'
