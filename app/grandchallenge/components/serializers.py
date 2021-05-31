from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.relations import SlugRelatedField

from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKind,
)
from grandchallenge.core.validators import JSONSchemaValidator
from grandchallenge.reader_studies.models import ANSWER_TYPE_SCHEMA


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
        queryset=Image.objects.all(),
        view_name="api:image-detail",
        required=False,
    )

    interface = SlugRelatedField(
        slug_field="slug", queryset=ComponentInterface.objects.all()
    )
    upload_session = serializers.HyperlinkedRelatedField(
        queryset=RawImageUploadSession.objects.all(),
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

    def validate(self, attrs):  # noqa: C901
        interface = attrs["interface"]

        def get_value():
            value = attrs.get("value", None)
            if not value:
                raise serializers.ValidationError(
                    f"Value is required for interface kind {interface.kind}"
                )
            return value

        def validate_simple():
            kind_to_type = {
                ComponentInterface.Kind.INTEGER: int,
                ComponentInterface.Kind.STRING: str,
                ComponentInterface.Kind.BOOL: bool,
                ComponentInterface.Kind.FLOAT: float,
            }
            value = get_value()
            if not isinstance(value, kind_to_type.get(interface.kind)):
                raise serializers.ValidationError(
                    f"Type of {value} does not match interface kind {interface.kind}"
                )

        def validate_annotations():
            value = get_value()
            allowed_types = [{"$ref": f"#/definitions/{interface.kind}"}]

            JSONSchemaValidator(
                schema={**ANSWER_TYPE_SCHEMA, "anyOf": allowed_types}
            )(value)

        def validate_image():
            # either image or upload_session should be provided
            if not any(key in attrs for key in ("upload_session", "image")):
                raise serializers.ValidationError(
                    f"Upload_session or image are required for interface kind {interface.kind}"
                )

        if interface.kind in InterfaceKind.interface_type_simple():
            validate_simple()
        if interface.kind in InterfaceKind.interface_type_annotation():
            validate_annotations()
        if interface.kind in InterfaceKind.interface_type_image():
            validate_image()

        return attrs

    def validate_upload_session(self, value):
        user = self.context.get("user")

        if not user.has_perm("view_rawimageuploadsession", value):
            raise serializers.ValidationError(
                f"User does not have permission to use {value}"
            )

        if value.status is not RawImageUploadSession.PENDING:
            raise serializers.ValidationError(
                f"{value} is not ready to be used"
            )
        return value

    def validate_image(self, value):
        user = self.context.get("user")

        if not user.has_perm("view_image", value):
            raise serializers.ValidationError(
                f"User does not have permission to use {value}"
            )
        return value


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
