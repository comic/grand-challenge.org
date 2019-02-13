from rest_framework import serializers
from grandchallenge.worklists.models import Worklist, WorklistItem, WorklistSet


class WorklistSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorklistSet
        fields = ("id", "title")


class WorklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worklist
        fields = ("id", "title", "set")


class WorklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorklistItem
        fields = ("id", "worklist", "image")
