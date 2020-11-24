from rest_framework import serializers

from grandchallenge.modalities.models import ImagingModality


class ImagingModalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagingModality
        fields = ["modality"]
