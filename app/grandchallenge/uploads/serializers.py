from rest_framework.serializers import ModelSerializer

from grandchallenge.uploads.models import UserUpload


class UserUploadSerializer(ModelSerializer):
    class Meta:
        model = UserUpload
        fields = (
            "pk",
            "created",
        )


class UserUploadFileSerializer(ModelSerializer):
    class Meta:
        model = UserUpload
        fields = (
            "pk",
            "created",
            "upload",
            "filename",
        )
