import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    PermissionDenied,
    ValidationError,
)
from django.db.models import OuterRef, Subquery
from django.forms.utils import ErrorList
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import LoginRequiredMixin
from guardian.shortcuts import assign_perm, get_perms
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.algorithms.filters import AlgorithmFilter, JobViewsetFilter
from grandchallenge.algorithms.forms import (
    AlgorithmDescriptionForm,
    AlgorithmForm,
    AlgorithmImageForm,
    AlgorithmImageUpdateForm,
    AlgorithmImportForm,
    AlgorithmInputsForm,
    AlgorithmPermissionRequestUpdateForm,
    AlgorithmPublishForm,
    AlgorithmRepoForm,
    AlgorithmUpdateForm,
    DisplaySetFromJobForm,
    JobForm,
    UsersForm,
    ViewersForm,
)
from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmPermissionRequest,
    Job,
)
from grandchallenge.algorithms.serializers import (
    AlgorithmImageSerializer,
    AlgorithmSerializer,
    HyperlinkedJobSerializer,
    JobPostSerializer,
)
from grandchallenge.algorithms.tasks import create_algorithm_jobs_for_session
from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.cases.widgets import WidgetChoices
from grandchallenge.components.models import (
    ComponentInterfaceValue,
    InterfaceKind,
)
from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.forms import UserFormKwargsMixin
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    PermissionListMixin,
    filter_by_permission,
)
from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.core.views import PermissionRequestUpdate
from grandchallenge.credits.models import Credit
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.github.models import GitHubUserToken
from grandchallenge.groups.forms import EditorsForm
from grandchallenge.groups.views import UserGroupUpdateMixin
from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.views import VerificationRequiredMixin

logger = logging.getLogger(__name__)


class AlgorithmCreate(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    VerificationRequiredMixin,
    UserFormKwargsMixin,
    CreateView,
):
    model = Algorithm
    form_class = AlgorithmForm
    permission_required = "algorithms.add_algorithm"

    def form_valid(self, form):
        response = super().form_valid(form=form)
        self.object.add_editor(self.request.user)
        return response


class AlgorithmList(FilterMixin, PermissionListMixin, ListView):
    model = Algorithm
    permission_required = "algorithms.view_algorithm"
    ordering = ("-highlight", "-created")
    filter_class = AlgorithmFilter
    paginate_by = 40

    def get_queryset(self):
        return super().get_queryset().prefetch_related("publications")

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context.update(
            {
                "jumbotron_title": "Algorithms",
                "jumbotron_description": format_html(
                    (
                        "We have made several machine learning algorithms "
                        "available that you can try out by uploading your "
                        "own anonymised medical imaging data. "
                        "Please <a href='{}'>contact us</a> if you would like "
                        "to make your own algorithm available here."
                    ),
                    mark_safe(
                        random_encode("mailto:support@grand-challenge.org")
                    ),
                ),
                "challenges_for_algorithms": cache.get(
                    "challenges_for_algorithms"
                ),
            }
        )
        return context


class AlgorithmDetail(ObjectPermissionRequiredMixin, DetailView):
    model = Algorithm
    permission_required = "algorithms.view_algorithm"
    raise_exception = True
    queryset = Algorithm.objects.prefetch_related(
        "algorithm_container_images__build__webhook_message",
        "algorithm_container_images__creator",
        "editors_group__user_set",
    )

    def on_permission_check_fail(self, request, response, obj=None):
        response = self.get(request)
        return response

    def check_permissions(self, request):
        """
        Checks if *request.user* has all permissions returned by
        *get_required_permissions* method.

        :param request: Original request.
        """
        try:
            return super().check_permissions(request)
        except PermissionDenied:
            return HttpResponseRedirect(
                reverse(
                    "algorithms:permission-request-create",
                    kwargs={"slug": self.object.slug},
                )
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form = UsersForm()
        form.fields["action"].initial = UsersForm.REMOVE
        editor_remove_form = EditorsForm()
        editor_remove_form.fields["action"].initial = EditorsForm.REMOVE

        context.update(
            {"form": form, "editor_remove_form": editor_remove_form}
        )

        pending_permission_requests = (
            AlgorithmPermissionRequest.objects.filter(
                algorithm=context["object"],
                status=AlgorithmPermissionRequest.PENDING,
            ).count()
        )
        context.update(
            {"pending_permission_requests": pending_permission_requests}
        )

        return context


class AlgorithmUpdate(
    LoginRequiredMixin,
    UserFormKwargsMixin,
    ObjectPermissionRequiredMixin,
    VerificationRequiredMixin,
    UpdateView,
):
    model = Algorithm
    form_class = AlgorithmUpdateForm
    permission_required = "algorithms.change_algorithm"
    raise_exception = True


class AlgorithmDescriptionUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    VerificationRequiredMixin,
    UpdateView,
):
    model = Algorithm
    form_class = AlgorithmDescriptionForm
    permission_required = "algorithms.change_algorithm"
    raise_exception = True


class AlgorithmUserGroupUpdateMixin(UserGroupUpdateMixin):
    template_name = "algorithms/user_groups_form.html"
    permission_required = "algorithms.change_algorithm"

    @property
    def obj(self):
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])


class JobUserGroupUpdateMixin(UserGroupUpdateMixin):
    template_name = "algorithms/user_groups_form.html"
    permission_required = "algorithms.change_job"

    @property
    def obj(self):
        return get_object_or_404(Job, pk=self.kwargs["pk"])


class EditorsUpdate(AlgorithmUserGroupUpdateMixin):
    form_class = EditorsForm
    success_message = "Editors successfully updated"

    def get_success_url(self):
        url = super().get_success_url()
        return f"{url}#editors"


class UsersUpdate(AlgorithmUserGroupUpdateMixin):
    form_class = UsersForm
    success_message = "Users successfully updated"

    def get_success_url(self):
        url = super().get_success_url()
        return f"{url}#users"


class JobViewersUpdate(JobUserGroupUpdateMixin):
    form_class = ViewersForm

    def get_success_message(self, cleaned_data):
        return format_html(
            (
                "Viewers for {} successfully updated. <br>"
                "They will be able to see the job by visiting {}"
            ),
            self.obj,
            self.obj.get_absolute_url(),
        )


class AlgorithmImageCreate(
    LoginRequiredMixin,
    VerificationRequiredMixin,
    UserFormKwargsMixin,
    ObjectPermissionRequiredMixin,
    CreateView,
):
    model = AlgorithmImage
    form_class = AlgorithmImageForm
    permission_required = "algorithms.change_algorithm"
    raise_exception = True

    @property
    def algorithm(self):
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"algorithm": self.algorithm})
        return kwargs

    def get_permission_object(self):
        return self.algorithm

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"algorithm": self.algorithm})
        return context


class AlgorithmImageDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = AlgorithmImage
    permission_required = "algorithms.view_algorithmimage"
    raise_exception = True
    queryset = AlgorithmImage.objects.prefetch_related(
        "build__webhook_message"
    )


class AlgorithmImageUpdate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView
):
    model = AlgorithmImage
    form_class = AlgorithmImageUpdateForm
    permission_required = "algorithms.change_algorithmimage"
    raise_exception = True

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"algorithm": self.object.algorithm})
        return context


class RemainingJobsMixin:
    @property
    def algorithm(self) -> Algorithm:
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def get_remaining_jobs(self, *, credits_per_job: int) -> dict:
        """
        Determines the number of jobs left for the user and when the next job can be started

        :return: A dictionary containing remaining_jobs (int) and
        next_job_at (datetime)
        """
        now = timezone.now()
        period = timedelta(days=30)
        user_credit = Credit.objects.get(user=self.request.user)

        if credits_per_job == 0:
            return {
                "remaining_jobs": 1,
                "next_job_at": now,
                "user_credits": user_credit.credits,
            }

        jobs = Job.credits_set.spent_credits(user=self.request.user)

        if jobs["oldest"]:
            next_job_at = jobs["oldest"] + period
        else:
            next_job_at = now

        if jobs["total"]:
            total_jobs = user_credit.credits - jobs["total"]
        else:
            total_jobs = user_credit.credits

        return {
            "remaining_jobs": int(total_jobs / max(credits_per_job, 1)),
            "next_job_at": next_job_at,
            "user_credits": total_jobs,
        }


class AlgorithmExecutionSessionCreate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UserFormKwargsMixin,
    CreateView,
    RemainingJobsMixin,
):
    model = RawImageUploadSession
    form_class = UploadRawImagesForm
    template_name = "algorithms/algorithm_execution_session_create.html"
    permission_required = "algorithms.execute_algorithm"
    raise_exception = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "linked_task": create_algorithm_jobs_for_session.signature(
                    kwargs={
                        "algorithm_image_pk": self.algorithm.latest_executable_image.pk
                    },
                    immutable=True,
                )
            }
        )
        return kwargs

    def get_permission_object(self):
        return self.algorithm

    def get_initial(self):
        if self.algorithm.latest_executable_image is None:
            raise Http404()
        return super().get_initial()

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"algorithm": self.algorithm})
        context.update(
            self.get_remaining_jobs(
                credits_per_job=self.algorithm.credits_per_job
            )
        )
        return context

    def get_success_url(self):
        return reverse(
            "algorithms:execution-session-detail",
            kwargs={"slug": self.kwargs["slug"], "pk": self.object.pk},
        )


class AlgorithmExperimentCreate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UserFormKwargsMixin,
    FormView,
    RemainingJobsMixin,
):
    form_class = AlgorithmInputsForm
    template_name = "algorithms/algorithm_inputs_form.html"
    permission_required = "algorithms.execute_algorithm"
    raise_exception = True

    def get_permission_object(self):
        return self.algorithm

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        kwargs.update({"algorithm": self.algorithm})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"algorithm": self.algorithm})
        context.update(
            self.get_remaining_jobs(
                credits_per_job=self.algorithm.credits_per_job
            )
        )
        return context

    def form_valid(self, form):
        def create_upload(image_files):
            upload_session = RawImageUploadSession.objects.create(
                creator=self.request.user
            )
            upload_session.user_uploads.set(image_files)
            return upload_session.pk

        job = Job.objects.create(
            creator=self.request.user,
            algorithm_image=self.algorithm.latest_executable_image,
        )

        # TODO AUG2021 JM permission management should be done in 1 place
        # The execution for jobs over the API or non-sessions needs
        # to be cleaned up. See callers of `execute_jobs`.
        job.viewer_groups.add(self.algorithm.editors_group)
        assign_perm("algorithms.view_logs", self.algorithm.editors_group, job)

        upload_pks = {}
        civs = []

        interfaces = {ci.slug: ci for ci in self.algorithm.inputs.all()}

        for slug, value in form.cleaned_data.items():
            ci = interfaces[slug]
            if ci.is_image_kind:
                if value:
                    widget = form.data[f"WidgetChoice-{ci.slug}"]
                    if widget == WidgetChoices.IMAGE_SEARCH:
                        (
                            civ,
                            created,
                        ) = ComponentInterfaceValue.objects.get_or_create(
                            interface=ci, image=value
                        )
                        if created:
                            civ.full_clean()
                            civ.save()
                        civs.append(civ)
                    elif widget == WidgetChoices.IMAGE_UPLOAD:
                        # create civ without image, image will be added when import completes
                        civ = ComponentInterfaceValue.objects.create(
                            interface=ci
                        )
                        civs.append(civ)
                        upload_pks[civ.pk] = create_upload(value)
                    else:
                        raise RuntimeError(
                            f"{widget} is not a valid widget choice."
                        )
            elif ci.requires_file:
                civ = ComponentInterfaceValue.objects.create(interface=ci)
                value.copy_object(to_field=civ.file)
                civ.full_clean()
                civ.save()
                value.delete()
                civs.append(civ)
            else:
                civ = ci.create_instance(value=value)
                civs.append(civ)

        job.inputs.add(*civs)
        job.run_job(upload_pks=upload_pks)

        return HttpResponseRedirect(
            reverse(
                "algorithms:job-experiment-detail",
                kwargs={"slug": self.kwargs["slug"], "pk": job.pk},
            )
        )


class JobExperimentDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    template_name = "algorithms/job_experiment_detail.html"
    permission_required = "algorithms.view_job"
    model = Job
    raise_exception = True

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("algorithm_image__algorithm")


class AlgorithmExecutionSessionDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = RawImageUploadSession
    template_name = "algorithms/executionsession_detail.html"
    permission_required = "cases.view_rawimageuploadsession"
    raise_exception = True

    @cached_property
    def algorithm(self):
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "algorithm": self.algorithm,
                "job_list_api_url": reverse("api:algorithms-job-list"),
            }
        )
        return context


class JobsList(PaginatedTableListView):
    model = Job
    row_template = "algorithms/job_list_row.html"
    search_fields = [
        "pk",
        "creator__username",
        "inputs__image__name",
        "inputs__image__files__file",
        "comment",
    ]
    default_sort_column = 1

    @cached_property
    def algorithm(self):
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def get_queryset(self):
        queryset = super().get_queryset()

        interface_values = {}
        for interface in self.outputs_list_display["JSON"]:
            interface_values[interface.slug] = Subquery(
                ComponentInterfaceValue.objects.filter(
                    interface=interface,
                    algorithms_jobs_as_output=OuterRef("pk"),
                ).values_list("value", flat=True)
            )

        queryset = (
            queryset.filter(algorithm_image__algorithm=self.algorithm)
            .annotate(**interface_values)
            .prefetch_related(
                "outputs__image__files",
                "outputs__interface",
                "inputs__image__files",
                "viewers__user_set",
            )
            .select_related(
                "creator__user_profile",
                "creator__verification",
                "algorithm_image__algorithm",
            )
        )

        return filter_by_permission(
            queryset=queryset,
            user=self.request.user,
            codename="view_job",
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "algorithm": self.algorithm,
                "columns": self.columns,
                "outputs_list_display": self.outputs_list_display,
            }
        )
        return context

    @cached_property
    def columns(self):
        columns = [
            Column(title="Details", sort_field="pk"),
            Column(title="Created", sort_field="created"),
            Column(title="Creator", sort_field="creator__username"),
            Column(title="Result", sort_field="status"),
            Column(title="Comment", sort_field="comment"),
            Column(title="Visibility", sort_field="public"),
            Column(title="Viewer", sort_field="status"),
        ]

        for key, grouped_interfaces in self.outputs_list_display.items():
            for interface in grouped_interfaces:
                if key == "JSON":
                    columns.append(
                        Column(
                            title=interface.title, sort_field=interface.slug
                        )
                    )
                else:
                    columns.append(Column(title=interface.title))

        return columns

    @cached_property
    def outputs_list_display(self):
        grouped_interfaces = {"JSON": [], "TIMG": [], "CHART": [], "FILE": []}

        for interface in self.algorithm.outputs.all():
            if interface.kind == InterfaceKind.InterfaceKindChoices.CHART:
                grouped_interfaces["CHART"].append(interface)
            elif interface.kind in (
                InterfaceKind.InterfaceKindChoices.PDF,
                InterfaceKind.InterfaceKindChoices.CSV,
                InterfaceKind.InterfaceKindChoices.ZIP,
                InterfaceKind.InterfaceKindChoices.SQREG,
            ):
                grouped_interfaces["FILE"].append(interface)
            elif interface.kind in {
                InterfaceKind.InterfaceKindChoices.THUMBNAIL_PNG,
                InterfaceKind.InterfaceKindChoices.THUMBNAIL_JPG,
            }:
                grouped_interfaces["TIMG"].append(interface)
            elif interface.kind in {
                InterfaceKind.InterfaceKindChoices.STRING,
                InterfaceKind.InterfaceKindChoices.INTEGER,
                InterfaceKind.InterfaceKindChoices.FLOAT,
                InterfaceKind.InterfaceKindChoices.BOOL,
            }:
                grouped_interfaces["JSON"].append(interface)

        return grouped_interfaces


class JobDetail(ObjectPermissionRequiredMixin, DetailView):
    permission_required = "algorithms.view_job"
    raise_exception = True
    queryset = (
        Job.objects.with_duration()
        .prefetch_related(
            "outputs__image__files",
            "outputs__interface",
            "inputs__image__files",
            "viewers__user_set__user_profile",
            "viewers__user_set__verification",
            "viewer_groups",
        )
        .select_related(
            "creator__user_profile",
            "creator__verification",
            "algorithm_image__algorithm__workstation",
        )
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        viewers_form = ViewersForm()
        viewers_form.fields["action"].initial = ViewersForm.REMOVE

        files = []
        thumbnails = []
        charts = []
        charts_data = []
        json = []
        for output in self.object.outputs.all():
            if (
                output.interface.kind
                == InterfaceKind.InterfaceKindChoices.CHART
            ):
                charts.append(output)
                charts_data.append(output.value)
            elif output.interface.kind in [
                InterfaceKind.InterfaceKindChoices.PDF,
                InterfaceKind.InterfaceKindChoices.CSV,
                InterfaceKind.InterfaceKindChoices.ZIP,
                InterfaceKind.InterfaceKindChoices.SQREG,
            ]:
                files.append(output)
            elif output.interface.kind in [
                InterfaceKind.InterfaceKindChoices.THUMBNAIL_PNG,
                InterfaceKind.InterfaceKindChoices.THUMBNAIL_JPG,
            ]:
                thumbnails.append(output)
            elif output.interface.kind in [
                InterfaceKind.InterfaceKindChoices.BOOL,
                InterfaceKind.InterfaceKindChoices.FLOAT,
                InterfaceKind.InterfaceKindChoices.INTEGER,
                InterfaceKind.InterfaceKindChoices.STRING,
            ]:
                json.append(output)

        context.update(
            {
                "viewers_form": viewers_form,
                "job_perms": get_perms(self.request.user, self.object),
                "charts": charts,
                "charts_data": charts_data,
                "files": files,
                "thumbnails": thumbnails,
                "json": json,
            }
        )

        return context


class JobUpdate(LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView):
    model = Job
    form_class = JobForm
    permission_required = "algorithms.change_job"
    raise_exception = True


class DisplaySetFromJobCreate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    FormView,
):
    form_class = DisplaySetFromJobForm
    permission_required = "algorithms.view_job"
    raise_exception = True
    template_name = "algorithms/display_set_from_job_form.html"

    @cached_property
    def job(self):
        return get_object_or_404(
            Job.objects.filter(status=Job.SUCCESS).prefetch_related(
                "inputs", "outputs", "algorithm_image__algorithm"
            ),
            pk=self.kwargs["pk"],
        )

    def get_permission_object(self):
        return self.job

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"object": self.job})
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def form_valid(self, form):
        display_set = self.job.get_or_create_display_set(
            reader_study=form.cleaned_data["reader_study"]
        )
        self.success_url = display_set.workstation_url

        return super().form_valid(form)


class AlgorithmViewSet(ReadOnlyModelViewSet):
    queryset = Algorithm.objects.all().prefetch_related("outputs", "inputs")
    serializer_class = AlgorithmSerializer
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]
    filterset_fields = ["slug"]


class AlgorithmImageViewSet(ReadOnlyModelViewSet):
    queryset = AlgorithmImage.objects.all()
    serializer_class = AlgorithmImageSerializer
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]
    filterset_fields = ["algorithm"]


class JobViewSet(
    CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet
):
    queryset = (
        Job.objects.all()
        .prefetch_related("outputs__interface", "inputs__interface")
        .select_related(
            "algorithm_image__algorithm__hanging_protocol",
        )
    )
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]
    filterset_class = JobViewsetFilter

    def get_serializer_class(self):
        if self.action == "create":
            return JobPostSerializer
        else:
            return HyperlinkedJobSerializer


class AlgorithmPermissionRequestCreate(
    LoginRequiredMixin, SuccessMessageMixin, CreateView
):
    model = AlgorithmPermissionRequest
    fields = ()

    @property
    def algorithm(self):
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def get_success_url(self):
        return self.algorithm.get_absolute_url()

    def get_success_message(self, cleaned_data):
        return self.object.status_to_string()

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.algorithm = self.algorithm
        try:
            redirect = super().form_valid(form)
            return redirect

        except ValidationError as e:
            form._errors[NON_FIELD_ERRORS] = ErrorList(e.messages)
            return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        permission_request = AlgorithmPermissionRequest.objects.filter(
            algorithm=self.algorithm, user=self.request.user
        ).first()
        context.update(
            {
                "permission_request": permission_request,
                "algorithm": self.algorithm,
            }
        )
        return context


class AlgorithmPermissionRequestList(ObjectPermissionRequiredMixin, ListView):
    model = AlgorithmPermissionRequest
    permission_required = "algorithms.change_algorithm"
    raise_exception = True

    @property
    def algorithm(self):
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.algorithm

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = (
            queryset.filter(algorithm=self.algorithm)
            .exclude(status=AlgorithmPermissionRequest.ACCEPTED)
            .select_related("user__user_profile", "user__verification")
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"algorithm": self.algorithm})
        return context


class AlgorithmPermissionRequestUpdate(PermissionRequestUpdate):
    model = AlgorithmPermissionRequest
    form_class = AlgorithmPermissionRequestUpdateForm
    base_model = Algorithm
    redirect_namespace = "algorithms"
    permission_required = "algorithms.change_algorithm"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"algorithm": self.base_object})
        return context


class AlgorithmAddRepo(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    VerificationRequiredMixin,
    UpdateView,
):
    model = Algorithm
    form_class = AlgorithmRepoForm
    template_name = "algorithms/algorithm_add_repo.html"
    permission_required = "algorithms.change_algorithm"
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "github_app_install_url": f"{settings.GITHUB_APP_INSTALL_URL}?state={self.object.slug}"
            }
        )
        return context

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()

        try:
            user_token = GitHubUserToken.objects.get(user=self.request.user)
        except GitHubUserToken.DoesNotExist:
            kwargs.update({"repos": []})
            return kwargs

        if user_token.refresh_token_is_expired:
            kwargs.update({"repos": []})
            return kwargs

        if user_token.access_token_is_expired:
            user_token.refresh_access_token()
            user_token.save()

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {user_token.access_token}",
        }
        params = {"per_page": 100, "page": 1}

        installations = requests.get(
            "https://api.github.com/user/installations",
            headers=headers,
            params=params,
            timeout=5,
        ).json()
        repos = []
        for installation in installations.get("installations", []):
            response = requests.get(
                f"https://api.github.com/user/installations/{installation['id']}/repositories",
                headers=headers,
                params=params,
                timeout=5,
            ).json()

            repos += [repo["full_name"] for repo in response["repositories"]]

        kwargs.update({"repos": repos})
        return kwargs


class AlgorithmPublishView(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = Algorithm
    form_class = AlgorithmPublishForm
    permission_required = "algorithms.change_algorithm"
    raise_exception = True

    def form_valid(self, form):
        super().form_valid(form)
        response = HttpResponse()
        response["HX-Refresh"] = "true"
        messages.add_message(
            self.request,
            messages.SUCCESS,
            "Your algorithm has been published successfully.",
        )
        return response


class AlgorithmImportView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = AlgorithmImportForm
    template_name = "algorithms/algorithm_import_form.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()

        self.success_url = form.algorithm.get_absolute_url()

        return super().form_valid(form=form)
