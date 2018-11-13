from rest_framework import serializers
from grandchallenge.worklists.models import Worklist, WorklistSet


class WorklistSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorklistSet
        fields = ("id", "title")


class WorklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worklist
        fields = ("id", "title", "set")
