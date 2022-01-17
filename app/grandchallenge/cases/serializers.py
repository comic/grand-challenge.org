import SimpleITK
from django.conf import settings
from django.http import Http404
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
    RawImageUploadSession,
)
from grandchallenge.cases.utils import get_sitk_image
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
                required=True,
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

        if "answer" in set_targets:
            # Link the answer to this upload session for image assignment later
            answer = set_targets["answer"]
            answer.answer = {"upload_session_pk": str(instance.pk)}
            answer.save()

        if set_targets:
            process_images(instance=instance, targets=set_targets)

        return instance

    def validate(self, attrs):
        attrs["creator"] = self.context["request"].user

        uploads = attrs.get("user_uploads", [])
        if len({f.filename for f in uploads}) != len(uploads):
            raise ValidationError("Filenames must be unique")

        num_targets = sum(f in attrs for f in self.targets)
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

        if value.answer is not None:
            raise ValidationError(
                "This answer already has an image assignment pending"
            )

        return value


def process_images(*, instance, targets):
    if instance.status != instance.PENDING:
        raise ValidationError("Session is not pending")

    instance.process_images(linked_task=_get_linked_task(targets=targets))


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


class CSImageSerializer(serializers.BaseSerializer):
    """
    Sserializes a cases.Image object into a Cornerstone image object as
    defined in https://docs.cornerstonejs.org/api.html#image.
    """

    def to_representation(self, instance):
        if instance.color_space not in (
            Image.COLOR_SPACE_GRAY,
            Image.COLOR_SPACE_RGBA,
            Image.COLOR_SPACE_RGB,
        ):
            raise Http404

        try:
            mh_file, _ = instance.get_metaimage_files()
            image_itk = get_sitk_image(image=instance)
            bit_depth = settings.SITK_PIXEL_TYPE_TO_BIT_DEPTH[
                image_itk.GetPixelIDValue()
            ]
        except (OSError, RuntimeError, IndexError) as e:
            raise Http404 from e

        # Finding min/max pixel values cannot be done on the client because it
        # is not supported in itk-wasm and a simple Math.min(...pixelValues)
        # will exceed max call stack size for large images. For non-grayscale
        # images we cannot use the built-in min/max filter so we resort to
        # setting the min/max allowed values for those pixel types.
        if instance.color_space == Image.COLOR_SPACE_GRAY:
            min_max_filter = SimpleITK.MinimumMaximumImageFilter()
            min_max_filter.Execute(image_itk)
            min_value = min_max_filter.GetMinimum()
            max_value = min_max_filter.GetMaximum()
        elif "unsigned" in image_itk.GetPixelIDTypeAsString():
            max_value = 2 ** bit_depth / 2
            min_value = -max_value
        else:
            min_value = 0
            max_value = 2 ** bit_depth

        return {
            "imageId": instance.pk,
            "minPixelValue": min_value,
            "maxPixelValue": max_value,
            "windowCenter": instance.window_center,
            "windowWidth": instance.window_width,
            "rows": instance.height,
            "columns": instance.width,
            "height": instance.height,
            "width": instance.width,
            "color": instance.color_space != Image.COLOR_SPACE_GRAY,
            "rgba": instance.color_space == Image.COLOR_SPACE_RGBA,
            "bit_depth": bit_depth,
            "mh_url": mh_file.file.url,
        }
