from django.shortcuts import render
from rest_framework import viewsets, permissions
from .models import Archive
from .serializers import ArchiveSerializer


class ArchiveViewSet(viewsets.ModelViewSet):
    queryset = Archive.objects.all()
    serializer_class = ArchiveSerializer
    permission_classes = (permissions.IsAuthenticated,)
