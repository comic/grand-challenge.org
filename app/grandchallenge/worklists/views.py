from grandchallenge.worklists.models import WorklistGroup, Worklist
from grandchallenge.worklists.serializer import WorklistGroupSerializer, WorklistSerializer
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend


class WorklistGroupTable(generics.ListCreateAPIView):
    queryset = WorklistGroup.objects.all()
    serializer_class = WorklistGroupSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = '__all__'


class WorklistGroupRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorklistGroup.objects.all()
    serializer_class = WorklistGroupSerializer


class WorklistTable(generics.ListCreateAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = '__all__'


class WorklistRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer


class WorklistGroupCreate(CreateView):
    model = WorklistGroup
    fields = '__all__'


class WorklistGroupUpdate(UpdateView):
    model = WorklistGroup
    fields = '__all__'


class WorklistGroupDelete(DeleteView):
    model = WorklistGroup
    success_url = reverse_lazy('groups')


class WorklistCreate(CreateView):
    model = Worklist
    fields = '__all__'


class WorklistUpdate(UpdateView):
    model = Worklist
    fields = '__all__'


class WorklistDelete(DeleteView):
    model = Worklist
    success_url = reverse_lazy('worklists')


#class WorklistPatientRelationTable(generics.ListCreateAPIView):
#    queryset = WorklistPatientRelation.objects.all()
#    serializer_class = WorklistPatientRelationSerializer
#    filter_backends = (DjangoFilterBackend,)
#    filter_fields = ('id', 'worklist', 'patient')


#class WorklistPatientRelationRecord(generics.RetrieveUpdateDestroyAPIView):
#    queryset = WorklistPatientRelation.objects.all()
#    serializer_class = WorklistPatientRelationSerializer
