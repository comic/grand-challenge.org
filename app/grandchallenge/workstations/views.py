from django.http import HttpResponse, Http404
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


class SessionCreate(UserIsStaffMixin, CreateView):
    model = Session
    fields = []

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.workstation = Workstation.objects.get(
            slug=self.kwargs["slug"]
        )
        return super().form_valid(form)


class SessionUpdate(UserIsStaffMixin, UpdateView):
    model = Session
    fields = ["user_finished"]


class SessionDetail(UserIsStaffMixin, DetailView):
    model = Session


def workstation_proxy(request, *, pk, path, **_):
    # TODO: pk.workstation is duplicated
    path = safe_join(f"/workstation-proxy/{pk}.workstation", path)
    user = request.user

    try:
        session = Session.objects.get(pk=pk)
    except Session.DoesNotExist:
        raise Http404("Session not found")

    if session.creator != user:
        raise Http404("Session not found")

    response = HttpResponse()
    response["X-Accel-Redirect"] = path

    return response
