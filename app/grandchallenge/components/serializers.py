import logging

from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.fields import CharField, SerializerMethodField
from rest_framework.relations import SlugRelatedField

from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.cases.widgets import DICOMUploadWithName
from grandchallenge.components.backends.exceptions import (
    CINotAllowedException,
    CIVNotEditableException,
)
from grandchallenge.components.models import (
    CIVData,
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.components.templatetags.civ import sort_civs
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.uploads.models import UserUpload
from grandchallenge.workstation_configs.serializers import (
    LookUpTableSerializer,
)

logger = logging.getLogger(__name__)


class ComponentInterfaceSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(source="get_kind_display", read_only=True)
    super_kind = SerializerMethodField()
    look_up_table = LookUpTableSerializer(read_only=True, allow_null=True)

    class Meta:
        model = ComponentInterface
        fields = [
            "title",
            "description",
            "slug",
            "kind",
            "pk",
            "default_value",
            "super_kind",
            "relative_path",
            "overlay_segments",
            "look_up_table",
        ]

    def get_super_kind(self, obj: ComponentInterface) -> str:
        return obj.super_kind.label


class SimpleImageSerializer(serializers.ModelSerializer):
    # Used for component interface values where only the user provided
    # name is needed
    class Meta:
        model = Image
        fields = ("pk", "name")


class ComponentInterfaceValuePostSerializer(serializers.ModelSerializer):
    """
    Serializes images with hyperlinks for external usage
    Expects interface_slug, to allow creating a ComponentInterfaceValue with an
    existing ComponentInterface
    """

    image = serializers.HyperlinkedRelatedField(
        queryset=Image.objects.none(),
        view_name="api:image-detail",
        required=False,
        allow_null=True,
    )
    interface = SlugRelatedField(
        slug_field="slug", queryset=ComponentInterface.objects.all()
    )
    upload_session = serializers.HyperlinkedRelatedField(
        queryset=RawImageUploadSession.objects.none(),
        view_name="api:upload-session-detail",
        required=False,
        write_only=True,
        allow_null=True,
    )
    user_upload = serializers.HyperlinkedRelatedField(
        queryset=UserUpload.objects.none(),
        view_name="api:upload-detail",
        required=False,
        write_only=True,
        allow_null=True,
    )
    image_name = CharField(required=False)

    class Meta:
        model = ComponentInterfaceValue
        fields = [
            "interface",
            "value",
            "file",
            "image",
            "pk",
            "upload_session",
            "user_upload",
            "image_name",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "request" in self.context:
            user = self.context["request"].user

            self.fields["image"].queryset = filter_by_permission(
                queryset=Image.objects.all(),
                user=user,
                codename="view_image",
            )

            self.fields["upload_session"].queryset = filter_by_permission(
                queryset=RawImageUploadSession.objects.filter(
                    status=RawImageUploadSession.PENDING
                ),
                user=user,
                codename="change_rawimageuploadsession",
            )

            self.fields["user_upload"].queryset = filter_by_permission(
                queryset=UserUpload.objects.all(),
                user=user,
                codename="change_userupload",
            )

            # Can't find a good way to set the dynamically generated queryset
            # for a field that gets used on POST, so create it here
            self.fields["user_uploads"] = serializers.HyperlinkedRelatedField(
                queryset=filter_by_permission(
                    queryset=UserUpload.objects.all(),
                    user=user,
                    codename="change_userupload",
                ),
                view_name="api:upload-detail",
                required=False,
                write_only=True,
                allow_null=True,
                many=True,
            )

    def validate(self, attrs):
        if "interface" not in attrs:
            raise serializers.ValidationError("An interface must be specified")

        interface = attrs["interface"]

        if interface.super_kind == interface.SuperKind.IMAGE:
            if interface.is_dicom_image_kind:
                self._validate_dicom_image(attrs, interface)
            else:
                self._validate_panimg_image(attrs, interface)
        elif interface.super_kind == interface.SuperKind.VALUE:
            if (
                attrs.get("value") is None
            ):  # Note: can also be False so check for None instead
                raise serializers.ValidationError(
                    f"value is required for interface "
                    f"kind {interface.kind}"
                )
        elif interface.super_kind == interface.SuperKind.FILE:
            if not any(
                [
                    attrs.get("file"),
                    attrs.get("user_upload"),
                ]
            ):
                raise serializers.ValidationError(
                    f"user_upload or file is required for interface "
                    f"kind {interface.kind}"
                )
        else:
            raise NotImplementedError(f"Unsupported interface {interface}")

        if (
            not attrs.get("upload_session")
            and not attrs.get("user_upload")
            and not attrs.get("user_uploads")
        ):
            # Instances without an image or a file are never valid, this will be checked
            # later, but for now check everything else. DRF 3.0 dropped calling
            # full_clean on instances, so we need to do it ourselves.
            instance = ComponentInterfaceValue(
                **{k: v for k, v in attrs.items() if v is not None}
            )
            instance.full_clean()

        return attrs

    def _validate_panimg_image(self, attrs, interface):
        if not any(
            [
                attrs.get("image"),
                attrs.get("upload_session"),
            ]
        ):
            raise serializers.ValidationError(
                f"upload_session or image are required for interface "
                f"kind {interface.kind}"
            )

    def _validate_dicom_image(self, attrs, interface):
        if not (
            attrs.get("image")
            or (attrs.get("user_uploads") and attrs.get("image_name"))
        ):
            raise serializers.ValidationError(
                f"either user_uploads with image_name, or image are "
                f"required for interface kind {interface.kind}"
            )


class SortedCIVSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        iterable = (
            data.all()
            if isinstance(data, serializers.models.manager.BaseManager)
            else data
        )
        sorted_data = sort_civs(iterable)
        return super().to_representation(sorted_data)


class ComponentInterfaceValueSerializer(serializers.ModelSerializer):
    # Serializes images in place rather than with hyperlinks for internal usage
    image = SimpleImageSerializer(required=False)
    interface = ComponentInterfaceSerializer()

    class Meta:
        model = ComponentInterfaceValue
        fields = ["interface", "value", "file", "image", "pk"]
        list_serializer_class = SortedCIVSerializer


class HyperlinkedComponentInterfaceValueSerializer(
    ComponentInterfaceValueSerializer
):
    # Serializes images with hyperlinks for external usage
    image = serializers.HyperlinkedRelatedField(
        view_name="api:image-detail",
        read_only=True,
        allow_null=True,
    )


class CIVSetPostSerializerMixin:

    editability_error_message = "This object cannot be updated."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["values"] = ComponentInterfaceValuePostSerializer(
            many=True,
            context=self.context,
            required=False,
        )

    def create(self, validated_data):
        if validated_data.pop("values", None):
            raise DRFValidationError("Values can only be added via update")
        return super().create(validated_data)

    def update(self, instance, validated_data):

        if not instance.is_editable:
            raise DRFValidationError(self.editability_error_message)

        values = validated_data.pop("values", [])

        instance = super().update(instance, validated_data)

        request = self.context["request"]

        civ_data_objects = []

        for value in values:
            interface = value["interface"]
            upload_session = value.get("upload_session")
            user_upload = value.get("user_upload")
            image = value.get("image")
            user_uploads = value.get("user_uploads")
            image_name = value.get("image_name")
            value = value.get("value")
            dicom_upload_with_name = (
                DICOMUploadWithName(name=image_name, user_uploads=user_uploads)
                if user_uploads and image_name
                else None
            )
            civ_data_objects.append(
                CIVData(
                    interface_slug=interface.slug,
                    value=upload_session
                    or user_upload
                    or image
                    or value
                    or dicom_upload_with_name,
                )
            )
        try:
            instance.validate_civ_data_objects_and_execute_linked_task(
                civ_data_objects=civ_data_objects, user=request.user
            )
        except CIVNotEditableException as e:
            error_handler = instance.get_error_handler()
            error_handler.handle_error(
                error_message="An unexpected error occurred",
                user=request.user,
            )
            logger.error(e, exc_info=True)
        except CINotAllowedException as e:
            raise DRFValidationError(e)

        if not self.partial:
            instance.refresh_from_db()
            current_civs = {
                civ.interface.slug: civ for civ in instance.values.all()
            }
            current_interfaces = set(current_civs.keys())
            updated_interfaces = {v["interface"].slug for v in values}
            for interface in current_interfaces - updated_interfaces:
                self.instance.remove_civ(civ=current_civs[interface])

        return instance
