from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework import generics

from grandchallenge.worklists.models import Worklist, WorklistSet
from grandchallenge.worklists.serializer import WorklistSerializer, WorklistSetSerializer
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.worklists.forms import (WorklistCreateForm,
                                            WorklistUpdateForm,
                                            WorklistSetCreateForm,
                                            WorklistSetUpdateForm)


## Worklist ###
class WorklistTable(generics.ListCreateAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer


class WorklistRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer


### Worklist Set ###
class WorklistSetTable(generics.ListCreateAPIView):
    queryset = WorklistSet.objects.all()
    serializer_class = WorklistSetSerializer


class WorklistSetRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorklistSet.objects.all()
    serializer_class = WorklistSetSerializer


class WorklistSetCreate(CreateView, UserIsStaffMixin):
    model = WorklistSet
    form_class = WorklistSetCreateForm
    template_name = 'worklists/set_details_form.html'

    def get_success_url(self):
        return reverse("worklists:set_list")


class WorklistSetUpdate(UpdateView, UserIsStaffMixin):
    model = WorklistSet
    form_class = WorklistSetUpdateForm
    template_name = 'worklists/set_details_form.html'

    def get_success_url(self):
        return reverse("worklists:set_list")


class WorklistSetDelete(DeleteView, UserIsStaffMixin):
    model = WorklistSet
    template_name = 'worklists/set_deletion_form.html'

    def get_success_url(self):
        return reverse("worklists:set_list")


class WorklistSetList(ListView, UserIsStaffMixin):
    model = WorklistSet
    paginate_by = 100
    template_name = 'worklists/set_list_form.html'
