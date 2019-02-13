from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework import generics
from grandchallenge.subdomains.utils import reverse
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.worklists.models import Worklist, WorklistItem, WorklistSet
from grandchallenge.worklists.serializers import (
    WorklistSerializer,
    WorklistItemSerializer,
    WorklistSetSerializer,
)
from grandchallenge.worklists.forms import (
    WorklistCreateForm,
    WorklistUpdateForm,
    WorklistItemCreateForm,
    WorklistItemUpdateForm,
    WorklistSetCreateForm,
    WorklistSetUpdateForm,
)

""" Worklist API Endpoints """


class WorklistTable(generics.ListCreateAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer


class WorklistRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer


""" WorklistItem API Endpoints """


class WorklistSetTable(generics.ListCreateAPIView):
    queryset = WorklistSet.objects.all()
    serializer_class = WorklistSetSerializer


class WorklistSetRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorklistSet.objects.all()
    serializer_class = WorklistSetSerializer


""" WorklistSet API Endpoints """


class WorklistItemTable(generics.ListCreateAPIView):
    queryset = WorklistItem.objects.all()
    serializer_class = WorklistItemSerializer


class WorklistItemRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorklistItem.objects.all()
    serializer_class = WorklistItemSerializer


""" Worklist Forms Views """


class WorklistCreateView(UserIsStaffMixin, CreateView):
    model = Worklist
    form_class = WorklistCreateForm

    def get_success_url(self):
        return reverse("worklists:list-display")


class WorklistRemoveView(UserIsStaffMixin, DeleteView):
    model = Worklist
    template_name = "worklists/worklist_remove_form.html"

    def get_success_url(self):
        return reverse("worklists:list-display")


class WorklistUpdateView(UserIsStaffMixin, UpdateView):
    model = Worklist
    form_class = WorklistUpdateForm

    def get_success_url(self):
        return reverse("worklists:list-display")


class WorklistDisplayView(UserIsStaffMixin, ListView):
    model = Worklist
    paginate_by = 100
    template_name = "worklists/worklist_display_form.html"


""" WorklistSet Forms Views """


class WorklistSetCreateView(UserIsStaffMixin, CreateView):
    model = WorklistSet
    form_class = WorklistSetCreateForm

    def get_success_url(self):
        return reverse("worklists:set-display")


class WorklistSetRemoveView(UserIsStaffMixin, DeleteView):
    model = WorklistSet
    template_name = "worklists/worklistset_remove_form.html"

    def get_success_url(self):
        return reverse("worklists:set-display")


class WorklistSetUpdateView(UserIsStaffMixin, UpdateView):
    model = WorklistSet
    form_class = WorklistSetUpdateForm

    def get_success_url(self):
        return reverse("worklists:set-display")


class WorklistSetDisplayView(UserIsStaffMixin, ListView):
    model = WorklistSet
    paginate_by = 100
    template_name = "worklists/worklistset_display_form.html"


""" WorklistItem Form Views """


class WorklistItemCreateView(UserIsStaffMixin, CreateView):
    model = WorklistItem
    form_class = WorklistItemCreateForm

    def get_success_url(self):
        return reverse("pathology:worklist-item-display")


class WorklistItemRemoveView(UserIsStaffMixin, DeleteView):
    model = WorklistItem
    template_name = "pathology/worklistitem_remove_form.html"

    def get_success_url(self):
        return reverse("pathology:worklist-item-display")


class WorklistItemUpdateView(UserIsStaffMixin, UpdateView):
    model = WorklistItem
    form_class = WorklistItemUpdateForm

    def get_success_url(self):
        return reverse("pathology:worklist-item-create")


class WorklistItemDisplayView(UserIsStaffMixin, ListView):
    model = WorklistItem
    paginate_by = 100
    template_name = "pathology/worklistitem_display_form.html"
