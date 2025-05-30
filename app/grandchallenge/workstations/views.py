import re
from datetime import timedelta
from urllib.parse import quote_plus

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls.resolvers import RoutePattern
from django.utils._os import safe_join
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import LoginRequiredMixin
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.viewsets import ReadOnlyModelViewSet
from ua_parser.user_agent_parser import ParseUserAgent

from grandchallenge.core.forms import UserFormKwargsMixin
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    ViewObjectPermissionListMixin,
    ViewObjectPermissionsFilter,
)
from grandchallenge.groups.forms import EditorsForm, UsersForm
from grandchallenge.groups.views import UserGroupUpdateMixin
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.subdomains.utils import reverse, reverse_lazy
from grandchallenge.verifications.views import VerificationRequiredMixin
from grandchallenge.workstations.forms import (
    DebugSessionForm,
    SessionForm,
    WorkstationForm,
    WorkstationImageForm,
    WorkstationImageMoveForm,
)
from grandchallenge.workstations.models import (
    Feedback,
    Session,
    Workstation,
    WorkstationImage,
)
from grandchallenge.workstations.serializers import (
    FeedbackSerializer,
    SessionSerializer,
    WorkstationSerializer,
)
from grandchallenge.workstations.utils import get_or_create_active_session


class SessionViewSet(ReadOnlyModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = (ViewObjectPermissionsFilter,)

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


class WorkstationList(
    LoginRequiredMixin, ViewObjectPermissionListMixin, ListView
):
    model = Workstation

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context.update({"jumbotron_title": "Viewers"})

        return context


class WorkstationCreate(PermissionRequiredMixin, CreateView):
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user_remove_form = UsersForm()
        user_remove_form.fields["action"].initial = UsersForm.REMOVE

        editor_remove_form = EditorsForm()
        editor_remove_form.fields["action"].initial = EditorsForm.REMOVE

        context.update(
            {
                "user_remove_form": user_remove_form,
                "editor_remove_form": editor_remove_form,
            }
        )
        return context


class WorkstationUpdate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView
):
    model = Workstation
    form_class = WorkstationForm
    permission_required = (
        f"{Workstation._meta.app_label}.change_{Workstation._meta.model_name}"
    )
    raise_exception = True


class WorkstationGroupUpdateMixin(UserGroupUpdateMixin):
    template_name = "workstations/workstation_user_groups_form.html"
    permission_required = (
        f"{Workstation._meta.app_label}.change_{Workstation._meta.model_name}"
    )

    @property
    def obj(self):
        return get_object_or_404(Workstation, slug=self.kwargs["slug"])


class WorkstationEditorsUpdate(WorkstationGroupUpdateMixin):
    form_class = EditorsForm
    success_message = "Editors successfully updated"


class WorkstationUsersUpdate(WorkstationGroupUpdateMixin):
    form_class = UsersForm
    success_message = "Users successfully updated"


class WorkstationImageCreate(
    LoginRequiredMixin,
    VerificationRequiredMixin,
    UserFormKwargsMixin,
    ObjectPermissionRequiredMixin,
    CreateView,
):
    model = WorkstationImage
    form_class = WorkstationImageForm
    permission_required = (
        f"{Workstation._meta.app_label}.change_{Workstation._meta.model_name}"
    )
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"workstation": self.workstation})
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"workstation": self.workstation})
        return kwargs

    @cached_property
    def workstation(self):
        return get_object_or_404(Workstation, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.workstation


class WorkstationImageDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = WorkstationImage
    permission_required = f"{WorkstationImage._meta.app_label}.view_{WorkstationImage._meta.model_name}"
    raise_exception = True


class WorkstationImageImportStatusDetail(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    DetailView,
):
    model = WorkstationImage
    permission_required = f"{WorkstationImage._meta.app_label}.view_{WorkstationImage._meta.model_name}"
    template_name = "components/import_status_detail.html"
    raise_exception = True
    login_url = reverse_lazy("account_login")


class WorkstationImageUpdate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView
):
    model = WorkstationImage
    fields = ("initial_path", "http_port", "websocket_port", "comment")
    template_name_suffix = "_update"
    permission_required = f"{WorkstationImage._meta.app_label}.change_{WorkstationImage._meta.model_name}"
    raise_exception = True


class WorkstationImageMove(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    FormView,
):
    form_class = WorkstationImageMoveForm
    template_name = "workstations/workstationimage_move.html"
    permission_required = f"{WorkstationImage._meta.app_label}.change_{WorkstationImage._meta.model_name}"
    raise_exception = True

    @cached_property
    def workstation_image(self):
        return get_object_or_404(WorkstationImage, pk=self.kwargs["pk"])

    def get_permission_object(self):
        return self.workstation_image

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "workstation_image": self.workstation_image,
                "user": self.request.user,
            }
        )
        return kwargs

    def get_success_url(self):
        return self.workstation_image.get_absolute_url()

    def form_valid(self, form):
        if form.cleaned_data["new_active_image"] is not None:
            form.cleaned_data["new_active_image"].mark_desired_version()

        workstation_image = form.cleaned_data["workstation_image"]

        workstation_image.workstation = form.cleaned_data["new_workstation"]
        workstation_image.save()

        workstation_image.mark_desired_version()

        redirect = super().form_valid(form=form)

        return redirect


class UnsupportedBrowserWarningMixin:
    def _get_unsupported_browser_message(self):
        user_agent = ParseUserAgent(self.request.headers.get("user-agent", ""))

        unsupported_browser = user_agent["family"].lower() not in [
            "firefox",
            "chrome",
            "edge",
            "safari",
        ]

        unsupported_chrome_version = (
            user_agent["family"].lower() == "chrome"
            and int(user_agent["major"]) < 79
        )

        if unsupported_browser:
            unsupported_browser_message = (
                "Unfortunately your browser is not supported. "
                "Please try again with the latest version of "
                "Firefox, Chrome, Edge or Safari."
            )
        elif unsupported_chrome_version:
            unsupported_browser_message = (
                "Unfortunately your version of Chrome is not supported. "
                "Please update to the latest version and try again."
            )
        else:
            unsupported_browser_message = None

        return unsupported_browser_message

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "unsupported_browser_message": self._get_unsupported_browser_message()
            }
        )
        return context


class SessionCreate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UnsupportedBrowserWarningMixin,
    CreateView,
):
    model = Session
    form_class = SessionForm
    permission_required = (
        f"{Workstation._meta.app_label}.view_{Workstation._meta.model_name}"
    )
    raise_exception = True

    @cached_property
    def workstation_image(self):
        slug = self.kwargs.get("slug", settings.DEFAULT_WORKSTATION_SLUG)

        workstation = get_object_or_404(Workstation, slug=slug)
        workstation_image = workstation.active_image

        if workstation_image is None:
            raise Http404("No container images found for this workstation")

        return workstation_image

    @cached_property
    def reader_study(self):
        workstation_path = self.kwargs.get("workstation_path", "")

        reader_study_pattern = RoutePattern(
            f"{settings.WORKSTATIONS_READY_STUDY_PATH_PARAM}/<uuid:pk>"
        )
        display_set_pattern = RoutePattern(
            f"{settings.WORKSTATIONS_DISPLAY_SET_PATH_PARAM}/<uuid:pk>"
        )

        if match := re.match(reader_study_pattern.regex, workstation_path):
            lookup = Q(pk=match.groupdict()["pk"])
        elif match := re.match(display_set_pattern.regex, workstation_path):
            lookup = Q(display_sets__pk=match.groupdict()["pk"])
        else:
            # Not a reader study path
            return

        return get_object_or_404(ReaderStudy, lookup)

    def get_permission_object(self):
        return self.workstation_image.workstation

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "object": self.workstation_image,
                "ping_endpoint": f"{self.request.site.domain.lower()}/ping",
            }
        )
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"reader_study": self.reader_study})
        return kwargs

    def form_valid(self, form):
        session = get_or_create_active_session(
            user=self.request.user,
            workstation_image=self.workstation_image,
            region=form.cleaned_data["region"],
            ping_times=form.cleaned_data.get("ping_times"),
            extra_env_vars=form.cleaned_data.get("extra_env_vars"),
        )

        workstation_path = self.kwargs.get("workstation_path", "")

        if self.reader_study:
            session.handle_reader_study_switching(
                reader_study=self.reader_study,
            )

        url = session.get_absolute_url()
        url += f"?path={quote_plus(workstation_path)}"
        qs = self.request.META.get("QUERY_STRING", "")
        if qs:
            url = f"{url}&qs={quote_plus(qs)}"

        return HttpResponseRedirect(url)


class DebugSessionCreate(SessionCreate):
    permission_required = (
        f"{Workstation._meta.app_label}.change_{Workstation._meta.model_name}"
    )
    form_class = DebugSessionForm
    template_name_suffix = "_debug_form"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "user": self.request.user,
                "workstation": self.workstation_image.workstation,
            }
        )
        return kwargs


class SessionDetail(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UnsupportedBrowserWarningMixin,
    DetailView,
):
    model = Session
    permission_required = (
        f"{Session._meta.app_label}.view_{Session._meta.model_name}"
    )
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "session_detail_url": reverse(
                    "api:session-detail", kwargs={"pk": self.object.pk}
                )
            }
        )
        return context


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


class FeedbackViewSet(mixins.CreateModelMixin, ReadOnlyModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = (ViewObjectPermissionsFilter,)


class WorkstationViewSet(ReadOnlyModelViewSet):
    queryset = Workstation.objects.all()
    serializer_class = WorkstationSerializer
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = [DjangoFilterBackend, ViewObjectPermissionsFilter]
    filterset_fields = ["slug"]
