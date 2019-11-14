from datetime import timedelta

from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils._os import safe_join
from django.utils.timezone import now
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    RedirectView,
    UpdateView,
)
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.core.permissions.rest_framework import (
    DjangoObjectOnlyPermissions,
)
from grandchallenge.workstations.forms import (
    EditorsForm,
    UsersForm,
    WorkstationForm,
    WorkstationImageForm,
)
from grandchallenge.workstations.models import (
    Session,
    Workstation,
    WorkstationImage,
)
from grandchallenge.workstations.serializers import SessionSerializer
from grandchallenge.workstations.utils import (
    get_or_create_active_session,
    get_workstation_image_or_404,
)


class SessionViewSet(ReadOnlyModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = (DjangoObjectOnlyPermissions,)
    filter_backends = (ObjectPermissionsFilter,)

    @action(detail=True, methods=["patch"])
    def keep_alive(self, *_, **__):
        """Increase the maximum duration of the session, up to the limit."""
        session = self.get_object()

        new_duration = now() + timedelta(minutes=5) - session.created
        duration_limit = timedelta(
            seconds=settings.WORKSTATIONS_SESSION_DURATION_LIMIT
        )

        if new_duration < duration_limit:
            session.maximum_duration = new_duration
            session.save()
            return Response({"status": "session extended"})
        else:
            session.maximum_duration = duration_limit
            session.save()
            return Response(
                {"status": "session duration limit reached"},
                status=HTTP_400_BAD_REQUEST,
            )


class WorkstationList(LoginRequiredMixin, PermissionListMixin, ListView):
    model = Workstation
    permission_required = (
        f"{Workstation._meta.app_label}.view_{Workstation._meta.model_name}"
    )


class WorkstationCreate(
    LoginRequiredMixin, PermissionRequiredMixin, CreateView
):
    model = Workstation
    form_class = WorkstationForm
    permission_required = (
        f"{Workstation._meta.app_label}.add_{Workstation._meta.model_name}"
    )

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.add_editor(user=self.request.user)
        return response


class WorkstationDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = Workstation
    permission_required = (
        f"{Workstation._meta.app_label}.view_{Workstation._meta.model_name}"
    )
    raise_exception = True


class WorkstationUpdate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView
):
    model = Workstation
    form_class = WorkstationForm
    permission_required = (
        f"{Workstation._meta.app_label}.change_{Workstation._meta.model_name}"
    )
    raise_exception = True


class WorkstationUsersAutocomplete(
    LoginRequiredMixin, UserPassesTestMixin, autocomplete.Select2QuerySetView
):
    def test_func(self):
        group_pks = (
            Workstation.objects.all()
            .select_related("editors_group")
            .values_list("editors_group__pk", flat=True)
        )
        return (
            self.request.user.is_superuser
            or self.request.user.groups.filter(pk__in=group_pks).exists()
        )

    def get_queryset(self):
        qs = (
            get_user_model()
            .objects.all()
            .order_by("username")
            .exclude(username=settings.ANONYMOUS_USER_NAME)
        )

        if self.q:
            qs = qs.filter(username__istartswith=self.q)

        return qs


class WorkstationGroupUpdateMixin(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    template_name = "workstations/workstation_user_groups_form.html"
    permission_required = (
        f"{Workstation._meta.app_label}.change_{Workstation._meta.model_name}"
    )
    raise_exception = True

    def get_permission_object(self):
        return self.workstation

    @property
    def workstation(self):
        return Workstation.objects.get(slug=self.kwargs["slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {"object": self.workstation, "role": self.get_form().role}
        )
        return context

    def get_success_url(self):
        return self.workstation.get_absolute_url()

    def form_valid(self, form):
        form.add_or_remove_user(workstation=self.workstation)
        return super().form_valid(form)


class WorkstationEditorsUpdate(WorkstationGroupUpdateMixin):
    form_class = EditorsForm
    success_message = "Editors successfully updated"


class WorkstationUsersUpdate(WorkstationGroupUpdateMixin):
    form_class = UsersForm
    success_message = "Users successfully updated"


class WorkstationImageCreate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, CreateView
):
    model = WorkstationImage
    form_class = WorkstationImageForm
    permission_required = (
        f"{Workstation._meta.app_label}.change_{Workstation._meta.model_name}"
    )
    raise_exception = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    @property
    def workstation(self):
        return Workstation.objects.get(slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.workstation

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.workstation = self.workstation

        uploaded_file = form.cleaned_data["chunked_upload"][0]
        form.instance.staged_image_uuid = uploaded_file.uuid

        return super().form_valid(form)


class WorkstationImageDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = WorkstationImage
    permission_required = f"{WorkstationImage._meta.app_label}.view_{WorkstationImage._meta.model_name}"
    raise_exception = True


class WorkstationImageUpdate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView
):
    model = WorkstationImage
    fields = ("initial_path", "http_port", "websocket_port")
    template_name_suffix = "_update"
    permission_required = f"{WorkstationImage._meta.app_label}.change_{WorkstationImage._meta.model_name}"
    raise_exception = True


class SessionRedirectView(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, RedirectView
):
    permanent = False
    permission_required = (
        f"{Workstation._meta.app_label}.view_{Workstation._meta.model_name}"
    )
    raise_exception = True

    def get_permission_object(self):
        return get_workstation_image_or_404(**self.kwargs).workstation

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


class SessionCreate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, CreateView
):
    model = Session
    fields = []
    permission_required = (
        f"{Workstation._meta.app_label}.view_{Workstation._meta.model_name}"
    )
    raise_exception = True

    @property
    def workstation(self):
        return Workstation.objects.get(slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.workstation

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.workstation_image = self.workstation.latest_ready_image
        return super().form_valid(form)


class SessionUpdate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView
):
    model = Session
    fields = ["user_finished"]
    permission_required = (
        f"{Session._meta.app_label}.change_{Session._meta.model_name}"
    )
    raise_exception = True


class SessionDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = Session
    permission_required = (
        f"{Session._meta.app_label}.view_{Session._meta.model_name}"
    )
    raise_exception = True


def session_proxy(request, *, pk, path, **_):
    """Return an internal redirect to the session instance if authorised."""
    session = get_object_or_404(Session, pk=pk)
    path = safe_join(f"/workstation-proxy/{session.hostname}", path)

    user = request.user
    if session.creator != user:
        raise PermissionDenied

    response = HttpResponse()
    response["X-Accel-Redirect"] = path

    return response
