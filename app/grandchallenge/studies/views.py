from rest_framework import viewsets, permissions
from .models import Study
from .serializers import StudySerializer


class StudyViewSet(viewsets.ModelViewSet):
    queryset = Study.objects.all()
    serializer_class = StudySerializer
    permission_classes = (permissions.IsAuthenticated,)
