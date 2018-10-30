from rest_framework import serializers
from grandchallenge.worklists.models import Worklist, WorklistGroup


class WorklistGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorklistGroup
        fields = '__all__'


class WorklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worklist
        fields = '__all__'


#class WorklistPatientRelationSerializer(serializers.ModelSerializer):
#    class Meta:
#        model = WorklistPatientRelation
#        fields = ('id', 'worklist', 'patient')
