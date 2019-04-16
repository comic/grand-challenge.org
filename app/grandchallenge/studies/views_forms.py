from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from grandchallenge.studies.models import Study
from grandchallenge.studies.forms import StudyForm
from grandchallenge.subdomains.utils import reverse
from grandchallenge.core.permissions.mixins import UserIsStaffMixin


class StudyCreateView(UserIsStaffMixin, CreateView):
    model = Study
    form_class = StudyForm

    def get_success_url(self):
        return reverse("studies:list")


class StudyDetailView(UserIsStaffMixin, DetailView):
    model = Study


class StudyDeleteView(UserIsStaffMixin, DeleteView):
    model = Study

    def get_success_url(self):
        return reverse("studies:")


class StudyUpdateView(UserIsStaffMixin, UpdateView):
    model = Study
    form_class = StudyForm

    def get_success_url(self):
        return reverse("studies:list")


class StudyListView(UserIsStaffMixin, ListView):
    model = Study
    paginate_by = 100
