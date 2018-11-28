from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework import generics


from grandchallenge.pathology.models import WorklistItem, PatientItem, StudyItem
from grandchallenge.pathology.serializer import WorklistItemSerializer, PatientItemSerializer, StudyItemSerializer
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.pathology.forms import (PatientItemCreateForm,
                                            PatientItemUpdateForm,
                                            StudyItemCreateForm,
                                            StudyItemUpdateForm,
                                            WorklistItemCreateForm,
                                            WorklistItemUpdateForm)


""" Patient Items """


class PatientItemTable(generics.ListCreateAPIView):
    queryset = PatientItem.objects.all()
    serializer_class = PatientItemSerializer


class PatientItemRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = PatientItem.objects.all()
    serializer_class = PatientItemSerializer


class PatientItemCreateView(UserIsStaffMixin, CreateView):
    model = PatientItem
    form_class = PatientItemCreateForm

    def get_success_url(self):
        return reverse("pathology:patient-item-display")


class PatientItemRemoveView(UserIsStaffMixin, DeleteView):
    model = PatientItem
    template_name = "pathology/patientitem_remove_form.html"

    def get_success_url(self):
        return reverse("pathology:patient-item-display")


class PatientItemUpdateView(UserIsStaffMixin, CreateView):
    model = PatientItem
    form_class = PatientItemUpdateForm

    def get_success_url(self):
        return reverse("pathology:patient-item-display")


class PatientDisplayView(UserIsStaffMixin, ListView):
    model = PatientItem
    paginate_by = 100
    template_name = "pathology/patientitem_display_form.html"


""" Study Items """


class StudyItemTable(generics.ListCreateAPIView):
    queryset = StudyItem.objects.all()
    serializer_class = StudyItemSerializer


class StudyItemRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = StudyItem.objects.all()
    serializer_class = StudyItemSerializer


class StudyItemCreateView(UserIsStaffMixin, CreateView):
    model = StudyItem
    form_class = StudyItemCreateForm

    def get_success_url(self):
        return reverse("pathology:study-item-display")


class StudyItemRemoveView(UserIsStaffMixin, DeleteView):
    model = StudyItem
    template_name = "pathology/studyitem_remove_form.html"

    def get_success_url(self):
        return reverse("pathology:study-item-display")


class StudyItemUpdateView(UserIsStaffMixin, CreateView):
    model = StudyItem
    form_class = StudyItemUpdateForm

    def get_success_url(self):
        return reverse("pathology:study-item-display")


class StudyDisplayView(UserIsStaffMixin, ListView):
    model = StudyItem
    paginate_by = 100
    template_name = "pathology/studyitem_display_form.html"


""" Worklist Items """


class WorklistItemTable(generics.ListCreateAPIView):
    queryset = WorklistItem.objects.all()
    serializer_class = WorklistItemSerializer


class WorklistItemRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorklistItem.objects.all()
    serializer_class = WorklistItemSerializer


class WorklistItemCreateView(UserIsStaffMixin, CreateView):
    model = StudyItem
    form_class = StudyItemCreateForm

    def get_success_url(self):
        return reverse("pathology:worklist-item-display")


class WorklistItemRemoveView(UserIsStaffMixin, DeleteView):
    model = StudyItem
    template_name = "pathology/worklistitem_remove_form.html"

    def get_success_url(self):
        return reverse("pathology:worklist-item-display")


class WorklistItemUpdateView(UserIsStaffMixin, CreateView):
    model = StudyItem
    form_class = StudyItemUpdateForm

    def get_success_url(self):
        return reverse("pathology:worklist-item-create")


class WorklistDisplayView(UserIsStaffMixin, ListView):
    model = StudyItem
    paginate_by = 100
    template_name = "pathology/worklistitem_display_form.html"
