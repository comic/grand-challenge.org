from rest_framework import serializers

from grandchallenge.api.swagger import swagger_schema_fields_for_charfield
from grandchallenge.cases.models import Image
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)


class ComponentInterfaceSerialzer(serializers.ModelSerializer):
    kind = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = ComponentInterface
        fields = [
            "title",
            "description",
            "slug",
            "kind",
            "pk",
        ]
        swagger_schema_fields = swagger_schema_fields_for_charfield(
            kind=model._meta.get_field("kind")
        )


class SimpleImageSerializer(serializers.ModelSerializer):
    # Used for component interface values where only the user provided
    # name is needed
    class Meta:
        model = Image
        fields = (
            "pk",
            "name",
        )


class ComponentInterfaceValueSerializer(serializers.ModelSerializer):
    # Serializes images in place rather than with hyperlinks for internal usage
    image = SimpleImageSerializer()
    interface = ComponentInterfaceSerialzer()

    class Meta:
        model = ComponentInterfaceValue
        fields = [
            "interface",
            "value",
            "file",
            "image",
            "pk",
        ]


class HyperlinkedComponentInterfaceValueSerializer(
    ComponentInterfaceValueSerializer
):
    # Serializes images with hyperlinks for external usage
    image = serializers.HyperlinkedRelatedField(
        queryset=Image.objects.all(), view_name="api:image-detail",
    )
