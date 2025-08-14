from django.conf import settings
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField
from rest_framework.relations import (
    HyperlinkedRelatedField,
    PrimaryKeyRelatedField,
    SlugRelatedField,
)

from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.archives.tasks import add_images_to_archive
from grandchallenge.cases.models import (
    Image,
    ImageFile,
    PostProcessImageTask,
    PostProcessImageTaskStatusChoices,
    RawImageUploadSession,
)
from grandchallenge.components.models import ComponentInterface
from grandchallenge.components.tasks import add_image_to_object
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.modalities.serializers import ImagingModalitySerializer
from grandchallenge.reader_studies.models import Answer, DisplaySet
from grandchallenge.reader_studies.tasks import add_image_to_answer
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
            "segments",
        )


class RawImageUploadSessionSerializer(serializers.ModelSerializer):
    image_set = HyperlinkedRelatedField(
        read_only=True, many=True, view_name="api:image-detail"
    )
    status = CharField(source="get_status_display", read_only=True)
    archive = SlugRelatedField(
        slug_field="slug",
        queryset=Archive.objects.none(),
        required=False,
        write_only=True,
    )
    answer = PrimaryKeyRelatedField(
        queryset=Answer.objects.none(),
        required=False,
        write_only=True,
    )
    interface = SlugRelatedField(
        slug_field="slug",
        queryset=ComponentInterface.objects.all(),
        required=False,
        write_only=True,
    )
    archive_item = PrimaryKeyRelatedField(
        queryset=ArchiveItem.objects.none(),
        required=False,
        write_only=True,
    )
    display_set = PrimaryKeyRelatedField(
        queryset=DisplaySet.objects.none(),
        required=False,
        write_only=True,
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
            "answer",
            "interface",
            "archive_item",
            "display_set",
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
                queryset=filter_by_permission(
                    queryset=UserUpload.objects.filter(
                        status=UserUpload.StatusChoices.COMPLETED
                    ),
                    user=user,
                    codename="change_userupload",
                ),
                view_name="api:upload-detail",
                required=True,
            )

            self.fields["archive"].queryset = filter_by_permission(
                queryset=Archive.objects.all(),
                user=user,
                codename="upload_archive",
            )

            self.fields["answer"].queryset = filter_by_permission(
                queryset=Answer.objects.all(),
                user=user,
                codename="change_answer",
            )

            self.fields["archive_item"].queryset = filter_by_permission(
                queryset=ArchiveItem.objects.all(),
                user=user,
                codename="change_archiveitem",
            )

            self.fields["display_set"].queryset = filter_by_permission(
                queryset=DisplaySet.objects.all(),
                user=user,
                codename="change_displayset",
            )

    @property
    def targets(self):
        return [
            "archive",
            "archive_item",
            "answer",
            "display_set",
        ]

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

        num_user_post_processing_tasks = PostProcessImageTask.objects.filter(
            status=PostProcessImageTaskStatusChoices.INITIALIZED,
            image__origin__creator=attrs["creator"],
        ).count()
        if (
            num_user_post_processing_tasks
            >= settings.CASES_MAX_NUM_USER_POST_PROCESSING_TASKS
        ):
            raise ValidationError(
                f"You currently have {num_user_post_processing_tasks} active image post processing tasks. "
                "Please wait for them to complete before trying again."
            )

        if len(uploads) > 100:
            raise ValidationError(
                "Too many files uploaded. A maximum of 100 files may be uploaded per session."
            )

        if len({f.filename for f in uploads}) != len(uploads):
            raise ValidationError("Filenames must be unique")

        num_targets = sum(f in attrs for f in self.targets)
        if num_targets > 1:
            raise ValidationError(
                "Only one of archive, archive item, answer or reader study can be set"
            )

        if "interface" in attrs and not (
            "archive" in attrs
            or "archive_item" in attrs
            or "display_set" in attrs
        ):
            raise ValidationError(
                "An interface can only be defined for archive, "
                "archive item or display set uploads."
            )

        if "archive_item" in attrs and "interface" not in attrs:
            raise ValidationError(
                "An interface needs to be defined to upload to an "
                "archive item."
            )

        if "display_set" in attrs and "interface" not in attrs:
            raise ValidationError(
                "An interface needs to be defined to upload to a "
                "display set."
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
        return add_image_to_object.signature(
            kwargs={
                "app_label": targets["archive_item"]._meta.app_label,
                "model_name": targets["archive_item"]._meta.model_name,
                "object_pk": targets["archive_item"].pk,
                "interface_pk": interface.pk,
            },
            immutable=True,
        )
    elif "display_set" in targets:
        return add_image_to_object.signature(
            kwargs={
                "app_label": targets["display_set"]._meta.app_label,
                "model_name": targets["display_set"]._meta.model_name,
                "object_pk": targets["display_set"].pk,
                "interface_pk": interface.pk,
            },
            immutable=True,
        )
    elif "answer" in targets:
        return add_image_to_answer.signature(
            kwargs={"answer_pk": targets["answer"].pk}, immutable=True
        )
    else:
        raise RuntimeError(f"Unknown target {targets=}")
