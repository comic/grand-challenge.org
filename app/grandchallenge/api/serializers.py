from rest_framework import serializers


class GCAPIVersionSerializer(serializers.Serializer):
    lowest_supported_version = serializers.CharField()
