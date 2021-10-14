from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.relations import SlugRelatedField

from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKind,
)


class ComponentInterfaceSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(source="get_kind_display", read_only=True)
    super_kind = SerializerMethodField()

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

    class Meta:
        model = ComponentInterfaceValue
        fields = [
            "interface",
            "value",
            "file",
            "image",
            "pk",
            "upload_session",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "request" in self.context:
            user = self.context["request"].user

            self.fields["image"].queryset = get_objects_for_user(
                user, "cases.view_image", accept_global_perms=False,
            )

            self.fields["upload_session"].queryset = get_objects_for_user(
                user,
                "cases.change_rawimageuploadsession",
                accept_global_perms=False,
            ).filter(status=RawImageUploadSession.PENDING)

    def validate(self, attrs):
        interface = attrs["interface"]

        if interface.kind in InterfaceKind.interface_type_image():
            if not attrs.get("image") and not attrs.get("upload_session"):
                raise serializers.ValidationError(
                    f"upload_session or image are required for interface "
                    f"kind {interface.kind}"
                )

            if attrs.get("image") and attrs.get("upload_session"):
                raise serializers.ValidationError(
                    "Only one of image or upload_session should be set"
                )

        if not attrs.get("upload_session"):
            # Instances without an image are never valid, this will be checked
            # later, but for now check everything else. DRF 3.0 dropped calling
            # full_clean on instances, so we need to do it ourselves.
            instance = ComponentInterfaceValue(
                **{k: v for k, v in attrs.items() if k != "upload_session"}
            )
            instance.full_clean()

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
