from pathology_worklist.api.models import Worklist, Patient, Study, Image, WorklistPatientRelation
from pathology_worklist.api.serializer import WorklistSerializer, PatientSerializer, StudySerializer, ImageSerializer, WorklistPatientRelationSerializer
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend


# List of views that can be queried
class WorklistTable(generics.ListCreateAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'title', 'parent', 'owner')


class WorklistRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer


class WorklistPatientRelationTable(generics.ListCreateAPIView):
    queryset = WorklistPatientRelation.objects.all()
    serializer_class = WorklistPatientRelationSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'worklist', 'patient')

class WorklistPatientRelationRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorklistPatientRelation.objects.all()
    serializer_class = WorklistPatientRelationSerializer
