from rest_framework import serializers

from grandchallenge.mlmodels.models import MLModel


class MLModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MLModel
        fields = (
            "pk",
            "created",
            "modified",
            "creator",
            "image_sha256",
            "ready",
            "status",
            "requires_gpu",
        )
