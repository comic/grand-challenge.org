from rest_framework import viewsets, permissions
from .models import OctObsRegistration
from .serializers import OctObsRegistrationSerializer


class OctObsRegistrationViewSet(viewsets.ModelViewSet):
    """
    Viewset for OctObsRegistration.
    This is currently only used in retina_importers app. Therefore, admin permissions are required.
    """
    queryset = OctObsRegistration.objects.all()
    serializer_class = OctObsRegistrationSerializer
    permission_classes = (permissions.IsAdminUser,)
