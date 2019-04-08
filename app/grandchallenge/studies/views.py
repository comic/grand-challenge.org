from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework import generics

from grandchallenge.studies.models import Study
from grandchallenge.studies.serializers import StudySerializer
from grandchallenge.studies.forms import StudyCreateForm, StudyUpdateForm
from grandchallenge.subdomains.utils import reverse
from grandchallenge.core.permissions.mixins import UserIsStaffMixin

""" Study API Endpoints """


class StudyTable(generics.ListCreateAPIView):
    serializer_class = StudySerializer

    def get_queryset(self):
        queryset = Study.objects.all()
        patient = self.request.query_params.get("patient", None)

        if patient is not None:
            queryset = queryset.filter(patient=patient)

        return queryset


class StudyRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Study.objects.all()
    serializer_class = StudySerializer


""" Study Form Views"""


class StudyCreateView(UserIsStaffMixin, CreateView):
    model = Study
    form_class = StudyCreateForm

    def get_success_url(self):
        return reverse("studies:study-display")


class StudyRemoveView(UserIsStaffMixin, DeleteView):
    model = Study
    template_name = "studies/study_remove_form.html"

    def get_success_url(self):
        return reverse("studies:study-display")


class StudyUpdateView(UserIsStaffMixin, UpdateView):
    model = Study
    form_class = StudyUpdateForm

    def get_success_url(self):
        return reverse("studies:study-display")


class StudyDisplayView(UserIsStaffMixin, ListView):
    model = Study
    paginate_by = 100
    template_name = "studies/study_display_form.html"
