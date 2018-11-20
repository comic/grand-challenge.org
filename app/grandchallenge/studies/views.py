from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework import generics

from grandchallenge.studies.models import Study
from grandchallenge.studies.serializer import StudySerializer
from grandchallenge.studies.forms import StudyCreateForm, StudyUpdateForm
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.core.permissions.mixins import UserIsStaffMixin


class StudyTable(generics.ListCreateAPIView):
    serializer_class = StudySerializer

    def get_queryset(self):
        # Get URL parameter as a string, if exists
        ids = self.request.query_params.get('ids', None)

        # Get snippets for ids if they exist
        if ids is not None:
            # Convert parameter string to list of integers
            ids = [int(x) for x in ids.split(',')]
            # Get objects for all parameter ids
            queryset = Study.objects.filter(pk__in=ids)

        else:
            # Else no parameters, return all objects
            queryset = Study.objects.all()

        return queryset


class StudyRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Study.objects.all()
    serializer_class = StudySerializer


class StudyCreate(CreateView, UserIsStaffMixin):
    model = Study
    form_class = StudyCreateForm

    def get_success_url(self):
        return reverse("studies:study_list")


class StudyUpdate(UpdateView, UserIsStaffMixin):
    model = Study
    form_class = StudyUpdateForm

    def get_success_url(self):
        return reverse("studies:study_list")


class StudyDelete(DeleteView, UserIsStaffMixin):
    model = Study
    template_name = "studies/study_deletion_form.html"

    def get_success_url(self):
        return reverse("studies:study_list")


class StudyList(ListView, UserIsStaffMixin):
    model = Study
    paginate_by = 100
    template_name = 'studies/study_list_form.html'
