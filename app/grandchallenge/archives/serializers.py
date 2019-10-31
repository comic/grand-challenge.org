from rest_framework import serializers

from grandchallenge.cases.serializers import ImageSerializer
from .models import Archive


class ArchiveSerializer(serializers.ModelSerializer):
    images = ImageSerializer(read_only=True, many=True)

    class Meta:
        model = Archive
        fields = ("id", "name", "images")
