from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from grandchallenge.pathology.models import WorklistItem, PatientItem, StudyItem
from grandchallenge.pathology.serializer import WorklistItemSerializer, PatientItemSerializer, StudyItemSerializer


class WorklistItemTable(generics.ListCreateAPIView):
    queryset = WorklistItem.objects.all()
    serializer_class = WorklistItemSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = '__all__'


class WorklistItemRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorklistItem.objects.all()
    serializer_class = WorklistItemSerializer


class PatientItemTable(generics.ListCreateAPIView):
    queryset = PatientItem.objects.all()
    serializer_class = PatientItemSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = '__all__'


class PatientItemRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = PatientItem.objects.all()
    serializer_class = PatientItemSerializer


class StudyItemTable(generics.ListCreateAPIView):
    queryset = StudyItem.objects.all()
    serializer_class = StudyItemSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = '__all__'


class StudyItemRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = StudyItem.objects.all()
    serializer_class = StudyItemSerializer
