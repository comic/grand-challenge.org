from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.workstation_configs.forms import WorkstationConfigForm
from grandchallenge.workstation_configs.models import WorkstationConfig
from grandchallenge.workstation_configs.serializers import (
    WorkstationConfigSerializer,
)


class WorkstationConfigViewSet(ReadOnlyModelViewSet):
    serializer_class = WorkstationConfigSerializer
    queryset = WorkstationConfig.objects.all()
    permission_classes = [IsAuthenticated]  # Note: this is a ReadOnlyView


class WorkstationConfigList(LoginRequiredMixin, ListView):
    model = WorkstationConfig


class WorkstationConfigCreate(
    LoginRequiredMixin, PermissionRequiredMixin, CreateView
):
    model = WorkstationConfig
    form_class = WorkstationConfigForm
    permission_required = f"{WorkstationConfig._meta.app_label}.add_{WorkstationConfig._meta.model_name}"

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super().form_valid(form)


class WorkstationConfigDetail(LoginRequiredMixin, DetailView):
    model = WorkstationConfig


class WorkstationConfigUpdate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView
):
    model = WorkstationConfig
    form_class = WorkstationConfigForm
    permission_required = f"{WorkstationConfig._meta.app_label}.change_{WorkstationConfig._meta.model_name}"
    raise_exception = True

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super().form_valid(form)


class WorkstationConfigDelete(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DeleteView
):
    model = WorkstationConfig
    permission_required = f"{WorkstationConfig._meta.app_label}.change_{WorkstationConfig._meta.model_name}"
    raise_exception = True
    success_message = "Workstation config was successfully deleted"

    def get_success_url(self):
        return reverse("workstation-configs:list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)
