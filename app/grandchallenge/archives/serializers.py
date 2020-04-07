from rest_framework import serializers
from rest_framework.fields import ReadOnlyField
from rest_framework.relations import HyperlinkedRelatedField

from grandchallenge.archives.models import Archive


class ArchiveSerializer(serializers.ModelSerializer):
    images = HyperlinkedRelatedField(
        read_only=True, many=True, view_name="api:image-detail"
    )
    # Include the read only name for legacy clients
    name = ReadOnlyField()

    class Meta:
        model = Archive
        fields = ("id", "name", "title", "images")
