from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.fields import JSONField, ReadOnlyField, URLField
from rest_framework.relations import HyperlinkedRelatedField

from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.components.serializers import (
    ComponentInterfaceValuePostSerializer,
    HyperlinkedComponentInterfaceValueSerializer,
)
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.hanging_protocols.serializers import (
    HangingProtocolSerializer,
)


class ArchiveItemSerializer(serializers.ModelSerializer):
    archive = HyperlinkedRelatedField(
        read_only=True, view_name="api:archive-detail"
    )
    values = HyperlinkedComponentInterfaceValueSerializer(many=True)
    hanging_protocol = HangingProtocolSerializer(
        source="archive.hanging_protocol", read_only=True, allow_null=True
    )
    optional_hanging_protocols = HangingProtocolSerializer(
        many=True,
        source="archive.optional_hanging_protocols",
        read_only=True,
        required=False,
    )
    view_content = JSONField(source="archive.view_content", read_only=True)

    class Meta:
        model = ArchiveItem
        fields = (
            "pk",
            "archive",
            "values",
            "hanging_protocol",
            "optional_hanging_protocols",
            "view_content",
        )


class ArchiveSerializer(serializers.ModelSerializer):
    algorithms = HyperlinkedRelatedField(
        read_only=True, many=True, view_name="api:algorithm-detail"
    )
    logo = URLField(source="logo.x20.url", read_only=True)
    url = URLField(source="get_absolute_url", read_only=True)
    # Include the read only name for legacy clients
    name = ReadOnlyField()

    class Meta:
        model = Archive
        fields = (
            "pk",
            "name",
            "title",
            "algorithms",
            "logo",
            "description",
            "api_url",
            "url",
        )


class ArchiveItemPostSerializer(ArchiveItemSerializer):
    archive = HyperlinkedRelatedField(
        queryset=Archive.objects.none(),
        view_name="api:archive-detail",
        write_only=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["values"] = ComponentInterfaceValuePostSerializer(
            many=True, context=self.context
        )

        if "request" in self.context:
            user = self.context["request"].user

            self.fields["archive"].queryset = filter_by_permission(
                queryset=Archive.objects.all(),
                user=user,
                codename="upload_archive",
            )

    def create(self, validated_data):
        if validated_data.pop("values") != []:
            raise DRFValidationError("Values can only be added via update")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        values = validated_data.pop("values")
        for value in values:
            interface = value.get("interface", None)
            user_upload = value.get("user_upload", None)
            image = value.get("image", None)
            value = value.get("value", None)
            instance.create_civ(
                ci_slug=interface.slug, new_value=user_upload or image or value
            )
        return instance
