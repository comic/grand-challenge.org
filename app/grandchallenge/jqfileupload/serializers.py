from rest_framework.fields import CharField, UUIDField, HiddenField
from rest_framework.serializers import ModelSerializer

from grandchallenge.jqfileupload.models import StagedFile


class StagedFileSerializer(ModelSerializer):
    filename = CharField(source="client_filename")
    uuid = UUIDField(source="file_id")
    extra_attrs = HiddenField(default=dict)

    class Meta:
        model = StagedFile
        fields = ("filename", "uuid", "extra_attrs")
