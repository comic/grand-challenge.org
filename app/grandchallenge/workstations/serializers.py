from rest_framework.fields import CharField
from rest_framework.serializers import ModelSerializer

from grandchallenge.api.swagger import swagger_schema_fields_for_charfield
from grandchallenge.workstations.models import Session


class SessionSerializer(ModelSerializer):
    status = CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Session
        fields = ("pk", "status")
        swagger_schema_fields = swagger_schema_fields_for_charfield(
            status=model._meta.get_field("status")
        )
