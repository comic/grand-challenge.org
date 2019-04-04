from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField

from grandchallenge.eyra_algorithms.models import Implementation, Job, Interface, Algorithm


class ImplementationSerializer(serializers.ModelSerializer):
    creator = PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Implementation
        fields = '__all__'


class AlgorithmSerializer(serializers.ModelSerializer):
    creator = PrimaryKeyRelatedField(read_only=True)

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
