from rest_framework import serializers
from rest_framework.relations import HyperlinkedRelatedField

from grandchallenge.cases.models import Image, ImageFile, RawImageUploadSession
from grandchallenge.algorithms.models import AlgorithmImage, Result
from grandchallenge.datasets.models import ImageSet, AnnotationSet
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
        allow_null=True,
        queryset=AlgorithmImage.objects.all(),
        view_name="api:algorithms-image-detail",
    )
    algorithm_result = HyperlinkedRelatedField(
        allow_null=True,
        queryset=Result.objects.all(),
        view_name="api:algorithms-result-detail",
    )
    annotationset = HyperlinkedRelatedField(
        allow_null=True,
        queryset=AnnotationSet.objects.all(),
        view_name="datasets:annotationset-detail",
    )
    imageset = HyperlinkedRelatedField(
        allow_null=True,
        queryset=ImageSet.objects.all(),
        view_name="api:image-detail",
    )
    reader_study = HyperlinkedRelatedField(
        allow_null=True,
        queryset=ReaderStudy.objects.all(),
        view_name="api:reader-study-detail",
    )

    class Meta:
        model = RawImageUploadSession
        fields = [
            "pk",
            "creator",
            "session_state",
            "error_message",
            "imageset",
            "algorithm",
            "algorithm_result",
            "annotationset",
            "reader_study",
            "api_url",
        ]
