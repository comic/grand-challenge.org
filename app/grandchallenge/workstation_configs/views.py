from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.workstation_configs.models import WorkstationConfig
from grandchallenge.workstation_configs.serializers import (
    WorkstationConfigSerializer,
)


class WorkstationConfigViewSet(ReadOnlyModelViewSet):
    serializer_class = WorkstationConfigSerializer
    queryset = WorkstationConfig.objects.all()
    permission_classes = [IsAuthenticated]  # Note: this is a ReadOnlyView
