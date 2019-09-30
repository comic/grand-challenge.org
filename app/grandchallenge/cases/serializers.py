from rest_framework import serializers
from rest_framework.relations import HyperlinkedRelatedField

from grandchallenge.cases.models import Image, ImageFile, RawImageUploadSession
from grandchallenge.algorithms.models import AlgorithmImage, Result
from grandchallenge.datasets.models import AnnotationSet
from grandchallenge.reader_studies.models import ReaderStudy


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
    algorithm = HyperlinkedRelatedField(
        queryset=AlgorithmImage.objects.all(),
        view_name="api:algorithms-image-detail",
    )
    algorithm_result = HyperlinkedRelatedField(
        queryset=Result.objects.all(), view_name="api:algorithms-result-detail"
    )

    class Meta:
        model = RawImageUploadSession
        fields = [
            "creator",
            "session_state",
            "error_message",
            "imageset",
            "algorithm",
            "algorithm_result",
            "api_url",
        ]
