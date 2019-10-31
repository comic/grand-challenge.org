from rest_framework import serializers

from grandchallenge.worklists.models import Worklist


class WorklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worklist
        fields = ("id", "title", "creator", "images")
