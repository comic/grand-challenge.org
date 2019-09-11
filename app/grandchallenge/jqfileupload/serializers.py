from rest_framework.fields import CharField, UUIDField, SerializerMethodField
from rest_framework.serializers import ModelSerializer

from grandchallenge.jqfileupload.models import StagedFile


class StagedFileSerializer(ModelSerializer):
    filename = CharField(source="client_filename")
    uuid = UUIDField(source="file_id")
    extra_attrs = SerializerMethodField(source="get_extra_attrs")

    class Meta:
        model = StagedFile
        fields = (
            "client_id",
            "csrf",  # TODO: Should be kept private?
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

    def get_extra_attrs(self, *_):
        return {}
