from rest_framework.serializers import ModelSerializer

from grandchallenge.workstations.models import Session


class SessionSerializer(ModelSerializer):
    class Meta:
        model = Session
        fields = ("pk", "status")
