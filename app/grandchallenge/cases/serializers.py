from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField
from rest_framework.relations import (
    HyperlinkedRelatedField,
    PrimaryKeyRelatedField,
    SlugRelatedField,
)

from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.archives.tasks import (
    add_images_to_archive,
    add_images_to_archive_item,
)
from grandchallenge.cases.models import Image, ImageFile, RawImageUploadSession
from grandchallenge.components.models import ComponentInterface
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
            "window_center",
            "window_width",
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
    interface = SlugRelatedField(
        slug_field="slug",
        queryset=ComponentInterface.objects.all(),
        required=False,
    )
    archive_item = PrimaryKeyRelatedField(
        queryset=ArchiveItem.objects.none(), required=False
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
            "interface",
            "archive_item",
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
                required=True,
            )

            self.fields["archive"].queryset = get_objects_for_user(
                user, "archives.upload_archive", accept_global_perms=False
            )

            self.fields["reader_study"].queryset = get_objects_for_user(
                user,
                "reader_studies.change_readerstudy",
                accept_global_perms=False,
            )

            self.fields["answer"].queryset = get_objects_for_user(
                user, "reader_studies.change_answer", accept_global_perms=False
            )

            self.fields["archive_item"].queryset = get_objects_for_user(
                user, "archives.change_archiveitem", accept_global_perms=False
            )

    @property
    def targets(self):
        return ["archive", "archive_item", "reader_study", "answer"]

    def create(self, validated_data):
        set_targets = {
            t: validated_data.pop(t)
            for t in self.targets
            if t in validated_data
        }
        interface = validated_data.pop("interface", None)

        instance = super().create(validated_data=validated_data)

        if "answer" in set_targets:
            # Link the answer to this upload session for image assignment later
            answer = set_targets["answer"]
            answer.answer = {"upload_session_pk": str(instance.pk)}
            answer.save()

        if set_targets:
            process_images(
                instance=instance, targets=set_targets, interface=interface
            )

        return instance

    def validate(self, attrs):
        attrs["creator"] = self.context["request"].user

        uploads = attrs.get("user_uploads", [])
        if len({f.filename for f in uploads}) != len(uploads):
            raise ValidationError("Filenames must be unique")

        num_targets = sum(f in attrs for f in self.targets)
        if num_targets > 1:
            raise ValidationError(
                "Only one of archive, archive item, answer or reader study can be set"
            )

        if "interface" in attrs and not (
            "archive" in attrs or "archive_item" in attrs
        ):
            raise ValidationError(
                "An interface can only be defined for archive "
                "or archive item uploads."
            )

        if "archive_item" in attrs and "interface" not in attrs:
            raise ValidationError(
                "An interface needs to be defined to upload to an "
                "archive item."
            )

        return attrs

    def validate_answer(self, value):
        if not value.question.is_image_type:
            raise ValidationError(
                "This question does not accept image type answers."
            )

        if value.answer is not None:
            raise ValidationError(
                "This answer already has an image assignment pending"
            )

        return value


def process_images(*, instance, targets, interface):
    if instance.status != instance.PENDING:
        raise ValidationError("Session is not pending")

    instance.process_images(
        linked_task=_get_linked_task(targets=targets, interface=interface)
    )


def _get_linked_task(*, targets, interface):
    if "archive" in targets:
        kwargs = {"archive_pk": targets["archive"].pk}
        if interface:
            kwargs["interface_pk"] = interface.pk
        return add_images_to_archive.signature(kwargs=kwargs, immutable=True)
    elif "archive_item" in targets:
        return add_images_to_archive_item.signature(
            kwargs={
                "archive_item_pk": targets["archive_item"].pk,
                "interface_pk": interface.pk,
            },
            immutable=True,
        )
    elif "reader_study" in targets:
        return add_images_to_reader_study.signature(
            kwargs={"reader_study_pk": targets["reader_study"].pk},
            immutable=True,
        )
    elif "answer" in targets:
        return add_image_to_answer.signature(
            kwargs={"answer_pk": targets["answer"].pk}, immutable=True
        )
    else:
        raise RuntimeError(f"Unknown target {targets=}")
