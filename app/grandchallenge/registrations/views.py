from django.shortcuts import render
from rest_framework import viewsets, permissions
from .models import OctObsRegistration
from .serializers import OctObsRegistrationSerializer


class OctObsRegistrationViewSet(viewsets.ModelViewSet):
    queryset = OctObsRegistration.objects.all()
    serializer_class = OctObsRegistrationSerializer
    permission_classes = (permissions.IsAuthenticated,)
