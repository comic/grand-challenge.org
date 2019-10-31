from rest_framework import viewsets

from grandchallenge.registrations.models import OctObsRegistration
from grandchallenge.registrations.serializers import (
    OctObsRegistrationSerializer,
)
from grandchallenge.retina_importers.mixins import RetinaImportPermission


class OctObsRegistrationViewSet(viewsets.ModelViewSet):
    """
    Viewset for OctObsRegistration.
    This is currently only used in retina_importers app. Therefore, admin
    permissions are required.
    """

    queryset = OctObsRegistration.objects.all()
    serializer_class = OctObsRegistrationSerializer
    permission_classes = (RetinaImportPermission,)
