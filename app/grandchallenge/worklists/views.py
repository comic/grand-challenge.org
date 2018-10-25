from grandchallenge.worklists.models import Worklist, WorklistPatientRelation
from grandchallenge.worklists.serializer import WorklistSerializer, WorklistPatientRelationSerializer
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend


# List of views that can be queried
class WorklistTable(generics.ListCreateAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'title', 'trunk', 'parent')


class WorklistRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer


#class WorklistPatientRelationTable(generics.ListCreateAPIView):
#    queryset = WorklistPatientRelation.objects.all()
#    serializer_class = WorklistPatientRelationSerializer
#    filter_backends = (DjangoFilterBackend,)
#    filter_fields = ('id', 'worklist', 'patient')


#class WorklistPatientRelationRecord(generics.RetrieveUpdateDestroyAPIView):
#    queryset = WorklistPatientRelation.objects.all()
#    serializer_class = WorklistPatientRelationSerializer
