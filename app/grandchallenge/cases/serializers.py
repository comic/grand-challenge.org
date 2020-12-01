from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField, SerializerMethodField
from rest_framework.relations import HyperlinkedRelatedField, SlugRelatedField

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.api.swagger import swagger_schema_fields_for_charfield
from grandchallenge.archives.models import Archive
from grandchallenge.cases.models import (
    Image,
    ImageFile,
    RawImageFile,
    RawImageUploadSession,
)
from grandchallenge.reader_studies.models import ReaderStudy


class ImageFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageFile
        fields = ("pk", "image", "file", "image_type")


class HyperlinkedImageSerializer(serializers.ModelSerializer):
    files = ImageFileSerializer(many=True, read_only=True)
    job_set = SerializerMethodField()
    archive_set = HyperlinkedRelatedField(
        read_only=True, many=True, view_name="api:archive-detail"
    )
    reader_study_set = HyperlinkedRelatedField(
        source="readerstudies",
        read_only=True,
        many=True,
        view_name="api:reader-study-detail",
    )

    def get_job_set(self, obj):
        return [
            job.api_url
            for civ in obj.componentinterfacevalue_set.all()
            for job in civ.algorithms_jobs_as_input.all()
        ]

    class Meta:
        model = Image
        fields = (
            "pk",
            "name",
            "study",
            "files",
            "reader_study_set",
            "archive_set",
            "job_set",
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
            "api_url",
        )


class RawImageUploadSessionSerializer(serializers.ModelSerializer):
    image_set = HyperlinkedRelatedField(
        read_only=True, many=True, view_name="api:image-detail"
    )
    status = CharField(source="get_status_display", read_only=True)

    class Meta:
        model = RawImageUploadSession
        fields = (
            "pk",
            "creator",
            "status",
            "error_message",
            "image_set",
            "api_url",
        )
        swagger_schema_fields = swagger_schema_fields_for_charfield(
            status=model._meta.get_field("status")
        )


class RawImageUploadSessionPatchSerializer(RawImageUploadSessionSerializer):
    algorithm = SlugRelatedField(
        slug_field="slug", queryset=Algorithm.objects.all(), required=False
    )
    archive = SlugRelatedField(
        slug_field="slug", queryset=Archive.objects.all(), required=False
    )
    reader_study = SlugRelatedField(
        slug_field="slug", queryset=ReaderStudy.objects.all(), required=False
    )

    class Meta(RawImageUploadSessionSerializer.Meta):
        fields = (
            *RawImageUploadSessionSerializer.Meta.fields,
            "algorithm",
            "archive",
            "reader_study",
        )

    def validate(self, attrs):
        if (
            sum(f in attrs for f in ["algorithm", "archive", "reader_study"])
            != 1
        ):
            raise ValidationError(
                "1 of algorithm, archive or reader study must be set"
            )
        return attrs

    def validate_algorithm(self, value):
        user = self.context.get("request").user

        if not user.has_perm("execute_algorithm", value):
            raise ValidationError(
                "User does not have permission to execute this algorithm"
            )

        if not value.latest_ready_image:
            raise ValidationError("This algorithm is not ready to be used")

        return value

    def validate_archive(self, value):
        user = self.context.get("request").user

        if not user.has_perm("upload_archive", value):
            raise ValidationError(
                "User does not have permission to upload to this archive"
            )

        return value

    def validate_reader_study(self, value):
        user = self.context.get("request").user

        if not user.has_perm("change_readerstudy", value):
            raise ValidationError(
                "User does not have permission to upload to this reader study"
            )

        return value


class RawImageFileSerializer(serializers.ModelSerializer):
    upload_session = HyperlinkedRelatedField(
        queryset=RawImageUploadSession.objects.all(),
        view_name="api:upload-session-detail",
    )

    def validate_upload_session(self, value):
        user = self.context.get("request").user

        if not user.has_perm("change_rawimageuploadsession", value):
            raise ValidationError(
                "User does not have permission to change this raw image upload session"
            )

        return value

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
