# -*- coding: utf-8 -*-
from rest_framework import serializers

from grandchallenge.cases.models import Image, ImageFile, Annotation


class ImageFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageFile
        fields = ("pk", "image", "file")


class ImageSerializer(serializers.ModelSerializer):
    files = ImageFileSerializer(many=True, read_only=True)

    class Meta:
        model = Image
        fields = ("pk", "name", "files")


class AnnotationSerializer(serializers.ModelSerializer):
    base = ImageSerializer(many=False, read_only=True)
    image = ImageSerializer(many=False, read_only=True)

    class Meta:
        model = Annotation
        fields = ("pk", "base", "image", "metadata")
