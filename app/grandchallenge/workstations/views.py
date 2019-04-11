from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils._os import safe_join
from django.views.generic import ListView, CreateView, DetailView, UpdateView

from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.workstations.forms import (
    WorkstationForm,
    WorkstationImageForm,
)
from grandchallenge.workstations.models import (
    Workstation,
    WorkstationImage,
    Session,
)


class WorkstationList(UserIsStaffMixin, ListView):
    model = Workstation


class WorkstationCreate(UserIsStaffMixin, CreateView):
    model = Workstation
    form_class = WorkstationForm


class WorkstationDetail(UserIsStaffMixin, DetailView):
    model = Workstation


class WorkstationUpdate(UserIsStaffMixin, UpdateView):
    model = Workstation
    form_class = WorkstationForm


class WorkstationImageCreate(UserIsStaffMixin, CreateView):
    model = WorkstationImage
    form_class = WorkstationImageForm

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.workstation = Workstation.objects.get(
            slug=self.kwargs["slug"]
        )

        uploaded_file = form.cleaned_data["chunked_upload"][0]
        form.instance.staged_image_uuid = uploaded_file.uuid

        return super().form_valid(form)


class WorkstationImageDetail(UserIsStaffMixin, DetailView):
    model = WorkstationImage


class WorkstationImageUpdate(UserIsStaffMixin, UpdateView):
    model = WorkstationImage
    fields = ("initial_path", "http_port", "websocket_port")
    template_name_suffix = "_update"


class SessionCreate(UserIsStaffMixin, CreateView):
    model = Session
    fields = []

    def form_valid(self, form):
        form.instance.creator = self.request.user
        workstation = Workstation.objects.get(slug=self.kwargs["slug"])
        form.instance.workstation_image = (
            workstation.workstationimage_set.filter(ready=True)
            .order_by("-created")
            .first()
        )
        return super().form_valid(form)


class SessionUpdate(UserIsStaffMixin, UpdateView):
    model = Session
    fields = ["user_finished"]


class SessionDetail(UserIsStaffMixin, DetailView):
    model = Session


def session_proxy(request, *, pk, path, **_):
    """ Returns an internal redirect to the session instance if authorised """
    session = get_object_or_404(Session, pk=pk)
    path = safe_join(f"/workstation-proxy/{session.hostname}", path)

    user = request.user
    if session.creator != user:
        raise PermissionDenied

    response = HttpResponse()
    response["X-Accel-Redirect"] = path

    return response
