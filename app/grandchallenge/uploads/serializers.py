from rest_framework.relations import HyperlinkedRelatedField
from rest_framework.serializers import ModelSerializer

from grandchallenge.uploads.models import UserUpload, UserUploadFile


class UserUploadSerializer(ModelSerializer):
    class Meta:
        model = UserUpload
        fields = (
            "pk",
            "created",
        )


class UserUploadFileSerializer(ModelSerializer):
    upload = HyperlinkedRelatedField(
        read_only=True, view_name="api:upload-detail"
    )

    class Meta:
        model = UserUploadFile
        fields = (
            "pk",
            "created",
            "upload",
            "filename",
        )
