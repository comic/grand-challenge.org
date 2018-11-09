from rest_framework import generics

from grandchallenge.pathology.models import WorklistItem, PatientItem, StudyItem
from grandchallenge.pathology.serializer import WorklistItemSerializer, PatientItemSerializer, StudyItemSerializer


class WorklistItemTable(generics.ListCreateAPIView):
    queryset = WorklistItem.objects.all()
    serializer_class = WorklistItemSerializer


class WorklistItemRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorklistItem.objects.all()
    serializer_class = WorklistItemSerializer


class PatientItemTable(generics.ListCreateAPIView):
    queryset = PatientItem.objects.all()
    serializer_class = PatientItemSerializer


class PatientItemRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = PatientItem.objects.all()
    serializer_class = PatientItemSerializer


class StudyItemTable(generics.ListCreateAPIView):
    queryset = StudyItem.objects.all()
    serializer_class = StudyItemSerializer


class StudyItemRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = StudyItem.objects.all()
    serializer_class = StudyItemSerializer
