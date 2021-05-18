from rest_framework import serializers

from grandchallenge.cases.models import Image
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKind,
)


class ComponentInterfaceSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = ComponentInterface
        fields = ["title", "description", "slug", "kind", "pk"]


class SimpleImageSerializer(serializers.ModelSerializer):
    # Used for component interface values where only the user provided
    # name is needed
    class Meta:
        model = Image
        fields = ("pk", "name")


class ComponentInterfaceValuePostSerializer(serializers.ModelSerializer):
    """
    Serializes images with hyperlinks for external usage
    Expects interface_title, to allow creating a ComponentInterfaceValue with an
    existing ComponentInterface
    """

    image = serializers.HyperlinkedRelatedField(
        queryset=Image.objects.all(),
        view_name="api:image-detail",
        required=False,
    )

    interface_title = serializers.CharField(write_only=True)

    class Meta:
        model = ComponentInterfaceValue
        fields = ["interface_title", "value", "file", "image", "pk"]

    def validate(self, attrs):
        interface = ComponentInterface.objects.get(
            title=attrs["interface_title"]
        )

        def kind_to_type(kind):
            if kind == ComponentInterface.Kind.INTEGER:
                return int
            if kind == ComponentInterface.Kind.STRING:
                return str
            if kind == ComponentInterface.Kind.BOOL:
                return bool
            if kind == ComponentInterface.Kind.FLOAT:
                return float
            return any

        def validate_simple():
            value = attrs["value"]
            if not isinstance(value, kind_to_type(interface.kind)):
                raise serializers.ValidationError(
                    f"{value} does not match interface kind {interface.kind}"
                )

        def validate_annotations():
            value = attrs["value"]
            # validate with json schema?

        if interface.kind in InterfaceKind.interface_type_simple():
            validate_simple()
        if interface.kind in InterfaceKind.interface_type_annotation():
            validate_annotations()

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
