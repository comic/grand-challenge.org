from rest_framework.fields import (
    CharField,
    IntegerField,
    SerializerMethodField,
)
from rest_framework.serializers import ModelSerializer, Serializer

from grandchallenge.uploads.models import UserUpload


class UserUploadSerializer(ModelSerializer):
    status = CharField(source="get_status_display", read_only=True)

    class Meta:
        model = UserUpload
        fields = (
            "pk",
            "created",
            "filename",
            "status",
        )
        read_only_fields = (
            "pk",
            "created",
            "status",
        )

    def validate(self, data):
        if data.get("creator") is None:
            data["creator"] = self.context["request"].user
        return data


class PresignedURLSerializer(Serializer):
    part_number = IntegerField(min_value=1, max_value=10_000, write_only=True)
    presigned_url = SerializerMethodField()

    def get_presigned_url(self, obj: UserUpload) -> str:
        return obj.generate_presigned_url(
            part_number=self.validated_data["part_number"]
        )


class PartSerializer(Serializer):
    e_tag = CharField()
    part_number = IntegerField(min_value=1, max_value=10_000)


class UserUploadCompleteSerializer(UserUploadSerializer):
    parts = PartSerializer(many=True, write_only=True)

    class Meta(UserUploadSerializer.Meta):
        fields = (
            *UserUploadSerializer.Meta.fields,
            "parts",
        )
        read_only_fields = (
            *UserUploadSerializer.Meta.read_only_fields,
            "filename",
        )

    def save(self, **kwargs):
        self.instance.complete_multipart_upload(
            parts=self.validated_data["parts"]
        )
        super().save(**kwargs)
