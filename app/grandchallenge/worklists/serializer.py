from rest_framework import serializers
from grandchallenge.worklists.models import Worklist, WorklistSet, WorklistTree


class WorklistSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorklistSet
        fields = '__all__'


class WorklistTreeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorklistTree
        fields = '__all__'


class WorklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worklist
        fields = '__all__'
