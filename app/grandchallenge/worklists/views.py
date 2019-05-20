from django.db import IntegrityError
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework import viewsets, status
from rest_framework.response import Response

from grandchallenge.cases.models import Image
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.subdomains.utils import reverse
from grandchallenge.worklists.forms import WorklistForm
from grandchallenge.worklists.models import Worklist
from grandchallenge.worklists.serializers import WorklistSerializer


class WorklistCreateView(UserIsStaffMixin, CreateView):
    model = Worklist
    form_class = WorklistForm

    def get_success_url(self):
        return reverse("worklists:list")


class WorklistDetailView(UserIsStaffMixin, DetailView):
    model = Worklist
    form_class = WorklistForm


class WorklistDeleteView(UserIsStaffMixin, DeleteView):
    model = Worklist

    def get_success_url(self):
        return reverse("worklists:list")


class WorklistUpdateView(UserIsStaffMixin, UpdateView):
    model = Worklist
    form_class = WorklistForm

    def get_success_url(self):
        return reverse("worklists:list")


class WorklistListView(UserIsStaffMixin, ListView):
    model = Worklist
    paginate_by = 100


class WorklistViewSet(viewsets.ModelViewSet):
    serializer_class = WorklistSerializer

    def create(self, request, *args, **kwargs):
        creator = request.user
        title = request.data.get("title", "")
        image_pks = request.data.get("images", "")

        worklist = Worklist.objects.create(title=title, creator=creator)
        if image_pks:
            #images = Image.objects.filter(pk__in=image_pks.split(","))
            #worklist.images.set(images)
            worklist.add(image_pks.split(","))
            worklist.save()

        serialized = WorklistSerializer(worklist)
        return Response(serialized.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        queryset = Worklist.objects.filter(creator=self.request.user.pk)
        return queryset
