from rest_framework import serializers
from grandchallenge.worklists.models import Worklist, WorklistPatientRelation


class WorklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worklist
        fields = ('id', 'title', 'parent', 'owner')


class WorklistPatientRelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorklistPatientRelation
        fields = ('id', 'worklist', 'patient')
