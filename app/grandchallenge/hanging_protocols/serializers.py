from rest_framework import serializers

from grandchallenge.hanging_protocols.models import HangingProtocol


class HangingProtocolSerializer(serializers.ModelSerializer):
    class Meta:
        model = HangingProtocol
        fields = ["title", "id", "json"]
