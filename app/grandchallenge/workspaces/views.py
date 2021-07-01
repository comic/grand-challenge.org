from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.views.generic import CreateView, DetailView, ListView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from ipware import get_client_ip

from grandchallenge.evaluation.models import Phase
from grandchallenge.workspaces.forms import WorkspaceForm
from grandchallenge.workspaces.models import Workspace


class WorkspaceList(PermissionListMixin, ListView):
    model = Workspace
    permission_required = "workspaces.view_workspace"


class WorkspaceCreate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, CreateView
):
    model = Workspace
    form_class = WorkspaceForm
    permission_required = "evaluation.create_phase_workspace"
    raise_exception = True

    def get_permission_object(self):
        return self.phase

    @cached_property
    def phase(self):
        return get_object_or_404(
            klass=Phase,
            slug=self.kwargs["slug"],
            challenge=self.request.challenge,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        client_ip, _ = get_client_ip(self.request)
        kwargs.update(
            {
                "user": self.request.user,
                "phase": self.phase,
                "allowed_ip": client_ip,
            }
        )

        return kwargs


class WorkspaceDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = Workspace
    permission_required = "workspaces.view_workspace"
    raise_exception = True
