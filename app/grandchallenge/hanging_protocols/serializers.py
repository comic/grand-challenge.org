from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from grandchallenge.hanging_protocols.models import HangingProtocol


class HangingProtocolSerializer(serializers.ModelSerializer):
    svg_icon = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_svg_icon(self, object):
        return object.svg_icon

    class Meta:
        model = HangingProtocol
        fields = ["json", "title", "pk", "svg_icon"]
