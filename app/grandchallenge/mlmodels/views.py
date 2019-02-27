from rest_framework import viewsets, permissions

from grandchallenge.mlmodels.models import MLModel
from grandchallenge.mlmodels.serializers import MLModelSerializer


class MLModelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MLModel.objects.all()
    serializer_class = MLModelSerializer
    permission_classes = (permissions.IsAdminUser,)
