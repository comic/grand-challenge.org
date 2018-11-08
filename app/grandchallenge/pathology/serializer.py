from rest_framework import serializers
from grandchallenge.pathology.models import WorklistItem, PatientItem, StudyItem


class WorklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorklistItem
        fields = ("id", "worklist", "study")


class PatientItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientItem
        fields = ("id", "patient", "study")


class StudyItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyItem
        fields = ("id", "study")
