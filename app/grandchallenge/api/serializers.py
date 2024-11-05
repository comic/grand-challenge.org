from rest_framework import serializers


class GCAPIVersionSerializer(serializers.Serializer):
    latest_version = serializers.CharField()
    lowest_supported_version = serializers.CharField()
