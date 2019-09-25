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
        # TODO: ensure that all of these are cleaned before creation
        extra_kwargs = {
            "client_id": {"write_only": True},
            "csrf": {"write_only": True},
            "end_byte": {"write_only": True},
            "file": {"write_only": True},
            "start_byte": {"write_only": True},
            "timeout": {"write_only": True},
            "total_size": {"write_only": True},
            "upload_path_sha256": {"write_only": True},
        }

    def get_extra_attrs(self, *_):
        return {}

    def validate(self, attrs):
        instance = StagedFile(**attrs)
        instance.clean()

        # This is set in the clean method
        attrs.update({"file_id": instance.file_id})

        return attrs
