from rest_framework.serializers import ModelSerializer

from grandchallenge.workstations.models import Workstation


class WorkstationSerializer(ModelSerializer):
    class Meta:
        model = Workstation
        fields = ("pk", "title", "slug", "description")
