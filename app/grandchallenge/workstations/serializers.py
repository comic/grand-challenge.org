from rest_framework.fields import CharField
from rest_framework.serializers import ModelSerializer

from grandchallenge.workstations.models import Session


class SessionSerializer(ModelSerializer):
    status = CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Session
        fields = ("pk", "status")
