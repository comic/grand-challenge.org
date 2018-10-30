from grandchallenge.studies.models import Study
from grandchallenge.studies.serializer import StudySerializer
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
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


class StudyCreate(CreateView):
    model = Study
    fields = '__all__'


class StudyUpdate(UpdateView):
    model = Study
    fields = '__all__'


class StudyDelete(DeleteView):
    model = Study
    success_url = reverse_lazy('studies')