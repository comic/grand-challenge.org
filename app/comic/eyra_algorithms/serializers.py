from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField

from comic.eyra_algorithms.models import Implementation, Job, Interface, Algorithm
from comic.eyra_users.serializers import Permissions


class ImplementationSerializer(serializers.ModelSerializer):
    creator = PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Implementation
        fields = '__all__'


class AlgorithmSerializer(serializers.ModelSerializer):
    creator = PrimaryKeyRelatedField(read_only=True)
    permissions = Permissions(source="*", read_only=True)

    class Meta:
        model = Algorithm
        fields = [*[f.name for f in Algorithm._meta.fields], 'permissions']


class InterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interface
        fields = '__all__'


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = '__all__'
