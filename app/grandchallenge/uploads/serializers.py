from rest_framework.fields import (
    CharField,
    IntegerField,
    SerializerMethodField,
)
from rest_framework.serializers import ModelSerializer, Serializer

from grandchallenge.uploads.models import UserUpload, UserUploadFile


class UserUploadSerializer(ModelSerializer):
    class Meta:
        model = UserUpload
        fields = (
            "pk",
            "created",
        )
        read_only_fields = (
            "pk",
            "created",
        )

    def validate(self, data):
        if data.get("creator") is None:
            data["creator"] = self.context["request"].user
        return data


class UserUploadFileSerializer(ModelSerializer):
    status = CharField(source="get_status_display", read_only=True)

    class Meta:
        model = UserUploadFile
        fields = (
            "pk",
            "created",
            "upload",
            "filename",
            "status",
        )
        read_only_fields = (
            "pk",
            "created",
            "status",
        )


class PresignedURLSerializer(Serializer):
    part_number = IntegerField(min_value=1, max_value=10_000, write_only=True)
    presigned_url = SerializerMethodField()

    def get_presigned_url(self, obj: UserUploadFile) -> str:
        return obj.generate_presigned_url(
            part_number=self.validated_data["part_number"]
        )


class PartSerializer(Serializer):
    e_tag = CharField()
    part_number = IntegerField(min_value=1, max_value=10_000)


class FileCompleteSerializer(UserUploadFileSerializer):
    parts = PartSerializer(many=True, write_only=True)

    class Meta(UserUploadFileSerializer.Meta):
        fields = (
            *UserUploadFileSerializer.Meta.fields,
            "parts",
        )
        read_only_fields = (
            *UserUploadFileSerializer.Meta.read_only_fields,
            "upload",
            "filename",
        )

    def save(self, **kwargs):
        self.instance.complete_multipart_upload(
            parts=self.validated_data["parts"]
        )
        super().save(**kwargs)
