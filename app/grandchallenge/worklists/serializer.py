from rest_framework import serializers
from grandchallenge.worklists.models import Group, Worklist


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'title')


class WorklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worklist
        fields = ('id', 'title', 'group', 'parent')


#class WorklistPatientRelationSerializer(serializers.ModelSerializer):
#    class Meta:
#        model = WorklistPatientRelation
#        fields = ('id', 'worklist', 'patient')
