from grandchallenge.worklists.models import Group, Worklist
from grandchallenge.worklists.serializer import GroupSerializer, WorklistSerializer
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend


class GroupTable(generics.ListCreateAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'title')


class GroupRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class WorklistTable(generics.ListCreateAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'title', 'trunk', 'parent')


class WorklistRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer


class GroupCreate(CreateView):
    model = Group
    fields = '__all__'


class GroupUpdate(UpdateView):
    model = Group
    fields = '__all__'


class GroupDelete(DeleteView):
    model = Group
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
