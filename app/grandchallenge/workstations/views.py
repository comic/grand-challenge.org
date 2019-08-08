from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils._os import safe_join
from django.views.generic import (
    ListView,
    CreateView,
    DetailView,
    UpdateView,
    RedirectView,
)
from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import ReadOnlyModelViewSet

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
from grandchallenge.workstations.serializers import SessionSerializer
from grandchallenge.workstations.utils import (
    get_workstation_image_or_404,
    get_or_create_active_session,
)


class SessionViewSet(ReadOnlyModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = (IsAdminUser,)


class WorkstationList(UserIsStaffMixin, ListView):
    model = Workstation


class WorkstationCreate(
    LoginRequiredMixin, PermissionRequiredMixin, CreateView
):
    model = Workstation
    form_class = WorkstationForm
    permission_required = (
        f"{Workstation._meta.app_label}.add_{Workstation._meta.model_name}"
    )


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


class SessionRedirectView(UserIsStaffMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        workstation_image = get_workstation_image_or_404(**kwargs)
        session = get_or_create_active_session(
            user=self.request.user, workstation_image=workstation_image
        )

        url = session.get_absolute_url()

        qs = self.request.META.get("QUERY_STRING", "")
        if qs:
            url = f"{url}?{qs}"

        return url


class SessionCreate(UserIsStaffMixin, CreateView):
    model = Session
    fields = []

    def form_valid(self, form):
        form.instance.creator = self.request.user
        workstation = Workstation.objects.get(slug=self.kwargs["slug"])
        form.instance.workstation_image = workstation.latest_ready_image
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
