from django.shortcuts import get_object_or_404
from django.views.generic import CreateView, DetailView, ListView
from ipware import get_client_ip

from grandchallenge.evaluation.models import Phase
from grandchallenge.workspaces.forms import WorkspaceForm
from grandchallenge.workspaces.models import Workspace


class WorkspaceList(ListView):
    model = Workspace


class WorkspaceCreate(CreateView):
    model = Workspace
    form_class = WorkspaceForm

    @property
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


class WorkspaceDetail(DetailView):
    model = Workspace
