from rest_framework.fields import CharField, UUIDField, HiddenField, DictField
from rest_framework.serializers import ModelSerializer

from grandchallenge.jqfileupload.models import StagedFile


class StagedFileSerializer(ModelSerializer):
    filename = CharField(source="client_filename", read_only=True)
    uuid = UUIDField(source="file_id", read_only=True)
    extra_attrs = DictField(read_only=True)

    class Meta:
        model = StagedFile
        fields = ("filename", "uuid", "extra_attrs")
