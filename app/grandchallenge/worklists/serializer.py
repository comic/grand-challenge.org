from rest_framework import serializers
from grandchallenge.worklists.models import Worklist, WorklistSet, WorklistSetNode


class WorklistSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorklistSet
        fields = '__all__'


class WorklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worklist
        fields = '__all__'


class WorklistSetNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorklistSetNode
        fields = '__all__'
