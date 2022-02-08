from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.components.models import ComponentInterface
from grandchallenge.components.serializers import ComponentInterfaceSerializer


class ComponentInterfaceViewSet(ReadOnlyModelViewSet):
    serializer_class = ComponentInterfaceSerializer
    queryset = ComponentInterface.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ("slug",)
    filter_backends = (DjangoFilterBackend,)
