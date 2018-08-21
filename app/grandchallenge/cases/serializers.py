# -*- coding: utf-8 -*-
from rest_framework import serializers

from grandchallenge.cases.models import Image, ImageFile, Annotation


class ImageFileSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ImageFile
        fields = ("image", "file",)


class AnnotationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Annotation
        fields = ("base", "image", "metadata",)


class ImageSerializer(serializers.HyperlinkedModelSerializer):
    files = ImageFileSerializer(many=True, read_only=True)
    annotations = AnnotationSerializer(many=True, read_only=True)

    class Meta:
        model = Image
        fields = ("name",)
        