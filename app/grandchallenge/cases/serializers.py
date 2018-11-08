from rest_framework import serializers

from grandchallenge.cases.models import Image, ImageFile


class ImageFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageFile
        fields = ("pk", "image", "file")


class ImageSerializer(serializers.ModelSerializer):
    files = ImageFileSerializer(many=True, read_only=True)

    class Meta:
        model = Image
        fields = ("pk", "name", "files")
