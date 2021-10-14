from django.conf import settings
from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField
from rest_framework.relations import (
    HyperlinkedRelatedField,
    PrimaryKeyRelatedField,
    SlugRelatedField,
)

from grandchallenge.archives.models import Archive
from grandchallenge.archives.tasks import add_images_to_archive
from grandchallenge.cases.models import (
    Image,
    ImageFile,
    RawImageFile,
    RawImageUploadSession,
)
from grandchallenge.jqfileupload.models import StagedFile
from grandchallenge.modalities.serializers import ImagingModalitySerializer
from grandchallenge.reader_studies.models import Answer, ReaderStudy
from grandchallenge.reader_studies.tasks import (
    add_image_to_answer,
    add_images_to_reader_study,
)
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
    archive = SlugRelatedField(
        slug_field="slug", queryset=Archive.objects.none(), required=False
    )
    reader_study = SlugRelatedField(
        slug_field="slug", queryset=ReaderStudy.objects.none(), required=False
    )
    answer = PrimaryKeyRelatedField(
        queryset=Answer.objects.none(), required=False
    )

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
            "archive",
            "reader_study",
            "answer",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "request" in self.context:
            user = self.context["request"].user

            # Can't find a good way to set the dynamically generated queryset
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

    @property
    def targets(self):
        return ["archive", "reader_study", "answer"]

    def create(self, validated_data):
        set_targets = {
            t: validated_data.pop(t)
            for t in self.targets
            if t in validated_data
        }

        instance = super().create(validated_data=validated_data)

        if instance.user_uploads.exists() and set_targets:
            # TODO WHEN_US_API_DEPRECATED instance.user_uploads.exists() will always be True
            process_images(instance=instance, targets=set_targets)

        return instance

    def validate(self, attrs):
        attrs["creator"] = self.context["request"].user

        uploads = attrs.get("user_uploads", [])
        if len({f.filename for f in uploads}) != len(uploads):
            raise ValidationError("Filenames must be unique")

        # TODO WHEN_US_API_DEPRECATED simplify this
        method = self.context["request"].method
        request_needs_target = bool(method == "PATCH")
        num_targets = sum(f in attrs for f in self.targets)

        if request_needs_target:
            if num_targets != 1:
                raise ValidationError(
                    "One of archive, answer or reader study must be set"
                )
        else:
            if num_targets > 1:
                raise ValidationError(
                    "Only one of archive, answer or reader study can be set"
                )

        return attrs

    def validate_answer(self, value):
        if not value.question.is_image_type:
            raise ValidationError(
                "This question does not accept image type answers."
            )
        return value


def process_images(*, instance, targets):
    if instance.status != instance.PENDING:
        raise ValidationError("Session is not pending")

    _validate_staged_files(staged_files=instance.rawimagefile_set.all())

    instance.process_images(linked_task=_get_linked_task(targets=targets))


def _validate_staged_files(*, staged_files):
    # TODO WHEN_US_API_DEPRECATED remove this method
    file_ids = [f.staged_file_id for f in staged_files]

    if any(f_id is None for f_id in file_ids):
        raise ValidationError("File has not been staged")

    chunks = StagedFile.objects.filter(file_id__in=file_ids)

    if len({c.client_filename for c in chunks}) != len(staged_files):
        raise ValidationError("Filenames must be unique")

    if any(f.consumed is True for f in staged_files):
        raise ValidationError("Some files have already been processed")

    if (
        sum([f.end_byte - f.start_byte for f in chunks])
        > settings.UPLOAD_SESSION_MAX_BYTES
    ):
        raise ValidationError(
            "Total size of all files exceeds the upload limit"
        )


def _get_linked_task(*, targets):
    if "archive" in targets:
        return add_images_to_archive.signature(
            kwargs={"archive_pk": targets["archive"].pk}, immutable=True,
        )
    elif "reader_study" in targets:
        return add_images_to_reader_study.signature(
            kwargs={"reader_study_pk": targets["reader_study"].pk},
            immutable=True,
        )
    elif "answer" in targets:
        return add_image_to_answer.signature(
            kwargs={"answer_pk": targets["answer"].pk}, immutable=True,
        )
    else:
        raise RuntimeError(f"Unknown target {targets=}")


class RawImageFileSerializer(serializers.ModelSerializer):
    # TODO WHEN_US_API_DEPRECATED remove this serializer
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
