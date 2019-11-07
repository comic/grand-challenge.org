from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.relations import HyperlinkedRelatedField

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.cases.models import (
    Image,
    ImageFile,
    RawImageFile,
    RawImageUploadSession,
)


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


class RawImageFileSerializer(serializers.ModelSerializer):
    upload_session = HyperlinkedRelatedField(
        queryset=RawImageUploadSession.objects.all(),
        view_name="api:upload-session-detail",
    )

    def validate(self, attrs):
        upload_session = attrs["upload_session"]
        user = self.context.get("request").user
        if upload_session.creator != user:
            raise ValidationError(
                f"User {user} does not have permission to see this raw image upload session "
            )
        return attrs

    class Meta:
        model = RawImageFile
        fields = ["pk", "upload_session", "filename", "api_url"]
