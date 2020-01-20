from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField
from rest_framework.relations import HyperlinkedRelatedField

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.api.swagger import swagger_schema_fields_for_charfield
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
            "voxel_width_mm",
            "voxel_height_mm",
            "voxel_depth_mm",
        )


class RawImageUploadSessionSerializer(serializers.ModelSerializer):
    algorithm_image = HyperlinkedRelatedField(
        queryset=AlgorithmImage.objects.all(),
        view_name="api:algorithms-image-detail",
    )
    status = CharField(source="get_status_display", read_only=True)

    def validate(self, attrs):
        algorithm_image = attrs["algorithm_image"]
        user = self.context.get("request").user
        if not user.has_perm("view_algorithm", algorithm_image.algorithm):
            raise ValidationError(
                f"User {user} does not have permission to view this algorithm "
            )
        return attrs

    class Meta:
        model = RawImageUploadSession
        fields = [
            "pk",
            "creator",
            "status",
            "error_message",
            "algorithm_image",
            "api_url",
        ]
        swagger_schema_fields = swagger_schema_fields_for_charfield(
            status=model._meta.get_field("status")
        )


class RawImageFileSerializer(serializers.ModelSerializer):
    upload_session = HyperlinkedRelatedField(
        queryset=RawImageUploadSession.objects.all(),
        view_name="api:upload-session-detail",
    )

    def validate(self, attrs):
        upload_session = attrs["upload_session"]
        user = self.context.get("request").user
        if not user.has_perm("change_rawimageuploadsession", upload_session):
            raise ValidationError(
                f"User {user} does not have permission to change this raw image upload session "
            )
        return attrs

    class Meta:
        model = RawImageFile
        fields = [
            "pk",
            "upload_session",
            "filename",
            "api_url",
            "consumed",
            "staged_file_id",
        ]
