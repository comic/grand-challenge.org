from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField
from rest_framework.relations import (
    HyperlinkedRelatedField,
    PrimaryKeyRelatedField,
    SlugRelatedField,
)

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.archives.models import Archive
from grandchallenge.cases.models import (
    Image,
    ImageFile,
    RawImageFile,
    RawImageUploadSession,
)
from grandchallenge.modalities.serializers import ImagingModalitySerializer
from grandchallenge.reader_studies.models import Answer, ReaderStudy
from grandchallenge.uploads.models import UserUpload


class ImageFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageFile
        fields = ("pk", "image", "file", "image_type")


class HyperlinkedImageSerializer(serializers.ModelSerializer):
    files = ImageFileSerializer(many=True, read_only=True)
    modality = ImagingModalitySerializer(allow_null=True, read_only=True)

    class Meta:
        model = Image
        fields = (
            "pk",
            "name",
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
            "api_url",
            "patient_id",
            "patient_name",
            "patient_birth_date",
            "patient_age",
            "patient_sex",
            "study_date",
            "study_instance_uid",
            "series_instance_uid",
            "study_description",
            "series_description",
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
            "user_uploads",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "request" in self.context:
            user = self.context["request"].user

            # Can't find a good way to set the dynamically queryset
            # for a field that gets used on POST, so create it here
            self.fields["uploads"] = HyperlinkedRelatedField(
                source="user_uploads",
                many=True,
                queryset=get_objects_for_user(
                    user,
                    "uploads.change_userupload",
                    accept_global_perms=False,
                ).filter(status=UserUpload.StatusChoices.COMPLETED),
                view_name="api:upload-detail",
                required=False,  # TODO WHEN_US_API_DEPRECATED set required=True
            )


class RawImageUploadSessionPatchSerializer(RawImageUploadSessionSerializer):
    algorithm = SlugRelatedField(
        slug_field="slug", queryset=Algorithm.objects.none(), required=False
    )
    archive = SlugRelatedField(
        slug_field="slug", queryset=Archive.objects.none(), required=False
    )
    reader_study = SlugRelatedField(
        slug_field="slug", queryset=ReaderStudy.objects.none(), required=False
    )
    answer = PrimaryKeyRelatedField(
        queryset=Answer.objects.none(), required=False
    )

    class Meta(RawImageUploadSessionSerializer.Meta):
        fields = (
            *RawImageUploadSessionSerializer.Meta.fields,
            "algorithm",
            "archive",
            "reader_study",
            "answer",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "request" in self.context:
            user = self.context["request"].user

            self.fields["algorithm"].queryset = get_objects_for_user(
                user,
                "algorithms.execute_algorithm",
                accept_global_perms=False,
            )

            self.fields["archive"].queryset = get_objects_for_user(
                user, "archives.upload_archive", accept_global_perms=False,
            )

            self.fields["reader_study"].queryset = get_objects_for_user(
                user,
                "reader_studies.change_readerstudy",
                accept_global_perms=False,
            )

            self.fields["answer"].queryset = get_objects_for_user(
                user,
                "reader_studies.change_answer",
                accept_global_perms=False,
            )

    def validate(self, attrs):
        if (
            sum(
                f in attrs
                for f in ["algorithm", "archive", "reader_study", "answer"]
            )
            != 1
        ):
            raise ValidationError(
                "1 of algorithm, archive, answer or reader study must be set"
            )
        return attrs

    def validate_algorithm(self, value):
        if not value.latest_ready_image:
            raise ValidationError("This algorithm is not ready to be used")
        return value

    def validate_answer(self, value):
        if not value.question.is_image_type:
            raise ValidationError(
                "This question does not accept image type answers."
            )
        return value


class RawImageFileSerializer(serializers.ModelSerializer):
    upload_session = HyperlinkedRelatedField(
        queryset=RawImageUploadSession.objects.none(),
        view_name="api:upload-session-detail",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "request" in self.context:
            user = self.context["request"].user

            self.fields["upload_session"].queryset = get_objects_for_user(
                user,
                "cases.change_rawimageuploadsession",
                accept_global_perms=False,
            )

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
