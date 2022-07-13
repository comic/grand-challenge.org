from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.relations import SlugRelatedField

from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.uploads.models import UserUpload
from grandchallenge.workstation_configs.serializers import (
    LookUpTableSerializer,
)


class ComponentInterfaceSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(source="get_kind_display", read_only=True)
    super_kind = SerializerMethodField()
    look_up_table = LookUpTableSerializer(read_only=True)

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
    )
    interface = SlugRelatedField(
        slug_field="slug", queryset=ComponentInterface.objects.all()
    )
    upload_session = serializers.HyperlinkedRelatedField(
        queryset=RawImageUploadSession.objects.none(),
        view_name="api:upload-session-detail",
        required=False,
        write_only=True,
    )
    user_upload = serializers.HyperlinkedRelatedField(
        queryset=UserUpload.objects.none(),
        view_name="api:upload-detail",
        required=False,
        write_only=True,
    )

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
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "request" in self.context:
            user = self.context["request"].user

            self.fields["image"].queryset = get_objects_for_user(
                user, "cases.view_image", accept_global_perms=False
            )

            self.fields["upload_session"].queryset = get_objects_for_user(
                user,
                "cases.change_rawimageuploadsession",
                accept_global_perms=False,
            ).filter(status=RawImageUploadSession.PENDING)

            self.fields["user_upload"].queryset = get_objects_for_user(
                user, "uploads.change_userupload", accept_global_perms=False
            )

    def validate(self, attrs):
        interface = attrs["interface"]
        attributes = [
            attribute for attribute in attrs if attribute != "interface"
        ]
        if len(attributes) > 1:
            raise serializers.ValidationError(
                "Only one of image, value, user_upload and "
                "upload_session should be set."
            )

        if interface.is_image_kind:
            if not attrs.get("image") and not attrs.get("upload_session"):
                raise serializers.ValidationError(
                    f"upload_session or image are required for interface "
                    f"kind {interface.kind}"
                )

        if not attrs.get("upload_session") and not attrs.get("user_upload"):
            # Instances without an image or a file are never valid, this will be checked
            # later, but for now check everything else. DRF 3.0 dropped calling
            # full_clean on instances, so we need to do it ourselves.
            instance = ComponentInterfaceValue(
                **{k: v for k, v in attrs.items() if k != "upload_session"}
            )
            instance.full_clean()

        if interface.is_file_kind:
            if not attrs.get("user_upload"):
                raise serializers.ValidationError(
                    f"user_upload is required for interface "
                    f"kind {interface.kind}"
                )

        return attrs


class ComponentInterfaceValueSerializer(serializers.ModelSerializer):
    # Serializes images in place rather than with hyperlinks for internal usage
    image = SimpleImageSerializer(required=False)
    interface = ComponentInterfaceSerializer()

    class Meta:
        model = ComponentInterfaceValue
        fields = ["interface", "value", "file", "image", "pk"]


class HyperlinkedComponentInterfaceValueSerializer(
    ComponentInterfaceValueSerializer
):
    # Serializes images with hyperlinks for external usage
    image = serializers.HyperlinkedRelatedField(
        queryset=Image.objects.all(), view_name="api:image-detail"
    )
