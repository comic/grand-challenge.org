from rest_framework import serializers
from .models import Archive
from grandchallenge.retina_images.serializers import RetinaImageSerializer


class ArchiveSerializer(serializers.ModelSerializer):
    images = RetinaImageSerializer(read_only=True, many=True)

    class Meta:
        model = Archive
        fields = ("id", "name", "images")
