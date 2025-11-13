import logging

from rest_framework import serializers
from rest_framework.fields import JSONField, URLField
from rest_framework.relations import HyperlinkedRelatedField

from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.components.serializers import (
    CIVSetPostSerializerMixin,
    HyperlinkedComponentInterfaceValueSerializer,
)
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.hanging_protocols.serializers import (
    HangingProtocolSerializer,
)

logger = logging.getLogger(__name__)


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
            "title",
            "archive",
            "values",
            "hanging_protocol",
            "optional_hanging_protocols",
            "view_content",
        )


class ArchiveSerializer(serializers.ModelSerializer):
    url = URLField(source="get_absolute_url", read_only=True)

    class Meta:
        model = Archive
        fields = (
            "pk",
            "title",
            "logo",
            "description",
            "api_url",
            "url",
        )


class ArchiveItemPostSerializer(
    CIVSetPostSerializerMixin,
    ArchiveItemSerializer,
):
    archive = HyperlinkedRelatedField(
        queryset=Archive.objects.none(),
        view_name="api:archive-detail",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "request" in self.context:
            user = self.context["request"].user
            self.fields["archive"].queryset = filter_by_permission(
                queryset=Archive.objects.all(),
                user=user,
                codename="upload_archive",
            )
