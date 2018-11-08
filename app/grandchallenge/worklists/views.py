from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend

from grandchallenge.worklists.models import Worklist, WorklistSet, WorklistSetNode
from grandchallenge.worklists.serializer import WorklistSerializer, WorklistSetSerializer, WorklistSetNodeSerializer
from grandchallenge.worklists.forms import WorklistSetDetailForm
from grandchallenge.core.urlresolvers import reverse


## Worklist ###
class WorklistTable(generics.ListCreateAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = '__all__'


class WorklistRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer


### Worklist Set ###
class WorklistSetTable(generics.ListCreateAPIView):
    queryset = WorklistSet.objects.all()
    serializer_class = WorklistSetSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = '__all__'


class WorklistSetRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorklistSet.objects.all()
    serializer_class = WorklistSetSerializer


class WorklistSetCreate(CreateView):
    model = WorklistSet
    form_class = WorklistSetDetailForm
    template_name = 'worklists/set_details_form.html'

    def get_success_url(self):
        return reverse("worklists:set_list")


class WorklistSetUpdate(UpdateView):
    model = WorklistSet
    form_class = WorklistSetDetailForm
    template_name = 'worklists/set_details_form.html'

    def get_success_url(self):
        return reverse("worklists:set_list")


class WorklistSetDelete(DeleteView):
    model = WorklistSet
    template_name = 'worklists/set_deletion_form.html'

    def get_success_url(self):
        return reverse("worklists:set_list")


class WorklistSetList(ListView):
    model = WorklistSet
    paginate_by = 100
    template_name = 'worklists/set_list_form.html'
