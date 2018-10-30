from rest_framework import serializers
from grandchallenge.pathology.models import WorklistItem, PatientItem, StudyItem


class WorklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorklistItem
        fields = '__all__'


class PatientItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientItem
        fields = '__all__'


class StudyItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyItem
        fields = '__all__'
