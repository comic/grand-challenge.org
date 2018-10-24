from grandchallenge.studies.models import Study
from grandchallenge.studies.serializer import StudySerializer
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend


class StudyTable(generics.ListCreateAPIView):
    queryset = Study.objects.all()
    serializer_class = StudySerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'region_of_interest')


class StudyRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Study.objects.all()
    serializer_class = StudySerializer
