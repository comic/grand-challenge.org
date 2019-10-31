from rest_framework import serializers

from grandchallenge.archives.models import Archive
from grandchallenge.cases.serializers import ImageSerializer


class ArchiveSerializer(serializers.ModelSerializer):
    images = ImageSerializer(read_only=True, many=True)

    class Meta:
        model = Archive
        fields = ("id", "name", "images")
