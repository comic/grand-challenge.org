from rest_framework.fields import CharField, UUIDField, SerializerMethodField
from rest_framework.serializers import ModelSerializer

from grandchallenge.jqfileupload.models import StagedFile


class StagedFileSerializer(ModelSerializer):
    filename = CharField(source="client_filename")
    uuid = UUIDField(source="file_id", read_only=True)
    extra_attrs = SerializerMethodField(source="get_extra_attrs")

    class Meta:
        model = StagedFile
        fields = (
            "client_id",
            "csrf",
            "end_byte",
            "extra_attrs",
            "file",
            "filename",
            "start_byte",
            "timeout",
            "total_size",
            "upload_path_sha256",
            "uuid",
        )
        extra_kwargs = {"csrf": {"write_only": True}}

    def get_extra_attrs(self, *_):
        return {}

    def validate(self, attrs):
        instance = StagedFile(**attrs)
        instance.clean()

        # This is set in the clean method
        attrs.update({"file_id": instance.file_id})

        return attrs
