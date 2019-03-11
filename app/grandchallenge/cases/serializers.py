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
        fields = (
            "pk",
            "name",
            "study",
            "files",
            "width",
            "height",
            "depth",
            "color_space",
            "modality",
            "eye_choice",
            "stereoscopic_choice",
            "field_of_view",
            "shape_without_color",
            "shape",
            "cirrus_link",
        )
