from pathlib import Path
from typing import Dict

from rest_framework.exceptions import ValidationError
from rest_framework.fields import (
    CharField,
    DateTimeField,
    IntegerField,
    ListField,
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
            "key",
            "s3_upload_id",
            "status",
            "api_url",
        )
        read_only_fields = (
            "pk",
            "created",
            "filename",
            "key",
            "s3_upload_id",
            "status",
            "api_url",
        )


class UserUploadCreateSerializer(UserUploadSerializer):
    class Meta(UserUploadSerializer.Meta):
        read_only_fields = [
            field
            for field in UserUploadSerializer.Meta.read_only_fields
            if field != "filename"
        ]

    def validate_filename(self, value):
        if value != Path(value).name:
            raise ValidationError(f"{value} is not a valid filename")
        return value

    def validate(self, data):
        if data.get("creator") is None:
            data["creator"] = self.context["request"].user
        return data


class PartSerializer(Serializer):
    ETag = CharField()
    PartNumber = IntegerField(min_value=1, max_value=10_000)
    LastModified = DateTimeField()
    Size = IntegerField(min_value=0)


class UserUploadPartsSerializer(UserUploadSerializer):
    parts = PartSerializer(source="list_parts", many=True, read_only=True)

    class Meta(UserUploadSerializer.Meta):
        fields = (
            *UserUploadSerializer.Meta.fields,
            "parts",
        )


class UserUploadPresignedURLsSerializer(UserUploadSerializer):
    part_numbers = ListField(
        child=IntegerField(min_value=1, max_value=10_000), write_only=True
    )
    presigned_urls = SerializerMethodField(read_only=True)

    class Meta(UserUploadSerializer.Meta):
        fields = (
            *UserUploadSerializer.Meta.fields,
            "part_numbers",
            "presigned_urls",
        )

    def validate(self, data):
        if "part_numbers" not in data:
            raise ValidationError("The `part_numbers` field is required")
        return data

    def get_presigned_urls(self, obj: UserUpload) -> Dict[int, str]:
        return obj.generate_presigned_urls(
            part_numbers=self.validated_data["part_numbers"]
        )


class UserUploadCompleteSerializer(UserUploadSerializer):
    parts = PartSerializer(many=True, write_only=True)

    class Meta(UserUploadSerializer.Meta):
        fields = (
            *UserUploadSerializer.Meta.fields,
            "parts",
        )

    def validate(self, data):
        if "parts" not in data:
            raise ValidationError("The `parts` field is required")
        return data

    def save(self, **kwargs):
        self.instance.complete_multipart_upload(
            parts=self.validated_data["parts"]
        )
        super().save(**kwargs)
