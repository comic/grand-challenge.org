from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.urls import reverse_lazy
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend

from grandchallenge.studies.models import Study
from grandchallenge.studies.serializer import StudySerializer
from grandchallenge.studies.forms import StudyDetailForm


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
    form_class = StudyDetailForm
    template_name = 'studies/study_details_form.html'
    success_url = reverse_lazy('studies:study_list')


class StudyUpdate(UpdateView):
    model = Study
    form_class = StudyDetailForm
    template_name = 'studies/study_details_form.html'
    success_url = reverse_lazy('studies:study_list')

class StudyDelete(DeleteView):
    model = Study
    template_name = 'studies/study_deletion_form.html'
    success_url = reverse_lazy('studies:study_list')


class StudyList(ListView):
    model = Study
    paginate_by = 100
    template_name = 'studies/patient_list_form.html'
