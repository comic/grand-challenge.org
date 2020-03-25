from rest_framework import serializers
from rest_framework.fields import ReadOnlyField

from grandchallenge.archives.models import Archive
from grandchallenge.cases.serializers import ImageSerializer


class ArchiveSerializer(serializers.ModelSerializer):
    images = ImageSerializer(read_only=True, many=True)
    # Include the read only name for legacy clients
    name = ReadOnlyField()

    class Meta:
        model = Archive
        fields = ("id", "name", "title", "images")
