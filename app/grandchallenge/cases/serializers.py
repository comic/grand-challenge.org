from rest_framework import serializers
from rest_framework.relations import HyperlinkedRelatedField

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.cases.models import Image, ImageFile, RawImageUploadSession


class ImageFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageFile
        fields = ("pk", "image", "file", "image_type")


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
        )


class RawImageUploadSessionSerializer(serializers.ModelSerializer):
    algorithm_image = HyperlinkedRelatedField(
        queryset=AlgorithmImage.objects.all(),
        view_name="api:algorithms-image-detail",
    )

    class Meta:
        model = RawImageUploadSession
        fields = [
            "pk",
            "creator",
            "session_state",
            "error_message",
            "algorithm_image",
            "api_url",
        ]
