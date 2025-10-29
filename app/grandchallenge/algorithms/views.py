import io
import logging
from pathlib import Path
from zipfile import ZipFile

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import (
    AccessMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, Window
from django.db.models.functions import Rank
from django.db.transaction import on_commit
from django.forms.utils import ErrorList
from django.http import FileResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)
from django_filters.rest_framework import DjangoFilterBackend
from grand_challenge_forge.forge import generate_algorithm_template
from guardian.mixins import LoginRequiredMixin
from guardian.shortcuts import get_perms
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from grandchallenge.algorithms.filters import AlgorithmFilter, JobViewsetFilter
from grandchallenge.algorithms.forms import (
    AlgorithmDescriptionForm,
    AlgorithmForm,
    AlgorithmImageForm,
    AlgorithmImageUpdateForm,
    AlgorithmImportForm,
    AlgorithmInterfaceForm,
    AlgorithmModelForm,
    AlgorithmModelUpdateForm,
    AlgorithmModelVersionControlForm,
    AlgorithmPermissionRequestUpdateForm,
    AlgorithmPublishForm,
    AlgorithmRepoForm,
    DisplaySetFromJobForm,
    ImageActivateForm,
    JobCreateForm,
    JobForm,
    JobInterfaceSelectForm,
    PhaseSelectForm,
    UsersForm,
    ViewersForm,
)
from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmAlgorithmInterface,
    AlgorithmImage,
    AlgorithmInterface,
    AlgorithmModel,
    AlgorithmPermissionRequest,
    Job,
)
from grandchallenge.algorithms.serializers import (
    AlgorithmImageSerializer,
    AlgorithmSerializer,
    HyperlinkedJobSerializer,
    JobPostSerializer,
)
from grandchallenge.components.backends.exceptions import (
    CIVNotEditableException,
)
from grandchallenge.components.models import (
    ImportStatusChoices,
    InterfaceKinds,
)
from grandchallenge.components.tasks import upload_to_registry_and_sagemaker
from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.forms import UserFormKwargsMixin
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    ViewObjectPermissionListMixin,
    ViewObjectPermissionsFilter,
    filter_by_permission,
)
from grandchallenge.core.templatetags.bleach import clean
from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.core.utils.grand_challenge_forge import (
    get_forge_algorithm_template_context,
)
from grandchallenge.core.views import PermissionRequestUpdate
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.evaluation.models import Evaluation
from grandchallenge.github.views import GitHubInstallationRequiredMixin
from grandchallenge.groups.forms import EditorsForm
from grandchallenge.groups.views import UserGroupUpdateMixin
from grandchallenge.subdomains.utils import reverse, reverse_lazy
from grandchallenge.verifications.views import VerificationRequiredMixin

logger = logging.getLogger(__name__)


class AlgorithmCreateRedirect(
    LoginRequiredMixin,
    VerificationRequiredMixin,
    FormView,
):
    form_class = PhaseSelectForm
    template_name = "algorithms/algorithm_create_redirect.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        phase = form.cleaned_data["phase"]
        self.success_url = reverse(
            "evaluation:phase-algorithm-create",
            kwargs={
                "challenge_short_name": phase.challenge.short_name,
                "slug": phase.slug,
            },
        )
        return super().form_valid(form=form)


class AlgorithmCreate(
    LoginRequiredMixin,
    PermissionRequiredMixin,
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


class AlgorithmList(FilterMixin, ViewObjectPermissionListMixin, ListView):
    model = Algorithm
    ordering = ("-highlight", "-created")
    filter_class = AlgorithmFilter
    paginate_by = 40

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                "publications",
                "optional_hanging_protocols",
            )
        )

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
                        "Please <a target='_blank' href='mailto:{support_email}'>contact support</a> if you "
                        "would like to make your own algorithm available here."
                    ),
                    support_email=clean(random_encode(settings.SUPPORT_EMAIL)),
                ),
                "challenges_for_algorithms": cache.get(
                    "challenges_for_algorithms"
                ),
            }
        )

        return context


class AlgorithmDetail(ObjectPermissionRequiredMixin, DetailView):
    model = Algorithm
    permission_required = "view_algorithm"
    raise_exception = True
    queryset = Algorithm.objects.prefetch_related(
        "algorithm_container_images__build__webhook_message",
        "algorithm_container_images__creator",
        "editors_group__user_set",
        "optional_hanging_protocols",
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

    @cached_property
    def best_evaluation_per_phase(self):
        return filter_by_permission(
            queryset=Evaluation.objects.select_related(
                "submission__phase__challenge"
            )
            .filter(
                submission__algorithm_image__algorithm=self.object, rank__gt=0
            )
            .annotate(
                phase_rank=Window(
                    expression=Rank(),
                    partition_by="submission__phase",
                    order_by=("rank", "created"),
                )
            )
            .filter(phase_rank=1)
            .order_by("created"),
            codename="view_evaluation",
            user=self.request.user,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form = UsersForm()
        form.fields["action"].initial = UsersForm.REMOVE
        editor_remove_form = EditorsForm()
        editor_remove_form.fields["action"].initial = EditorsForm.REMOVE

        pending_permission_requests = (
            AlgorithmPermissionRequest.objects.filter(
                algorithm=context["object"],
                status=AlgorithmPermissionRequest.PENDING,
            ).count()
        )

        editors = list(self.object.editors_group.user_set.all())
        editors.reverse()  # Reverse order to show original creator first.

        context.update(
            {
                "form": form,
                "editor_remove_form": editor_remove_form,
                "pending_permission_requests": pending_permission_requests,
                "algorithm_perms": get_perms(self.request.user, self.object),
                "best_evaluation_per_phase": self.best_evaluation_per_phase,
                "editors": editors,
            }
        )

        return context


class AlgorithmStatistics(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = Algorithm
    permission_required = "change_algorithm"
    template_name = "algorithms/algorithm_statistics.html"
    raise_exception = True


class AlgorithmUpdate(
    LoginRequiredMixin,
    UserFormKwargsMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = Algorithm
    form_class = AlgorithmForm
    permission_required = "change_algorithm"
    raise_exception = True


class AlgorithmDescriptionUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = Algorithm
    form_class = AlgorithmDescriptionForm
    permission_required = "change_algorithm"
    raise_exception = True


class AlgorithmUserGroupUpdateMixin(UserGroupUpdateMixin):
    template_name = "algorithms/user_groups_form.html"
    permission_required = "change_algorithm"

    @property
    def obj(self):
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])


class JobUserGroupUpdateMixin(UserGroupUpdateMixin):
    template_name = "algorithms/user_groups_form.html"
    permission_required = "change_job"

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
    SuccessMessageMixin,
    CreateView,
):
    model = AlgorithmImage
    form_class = AlgorithmImageForm
    permission_required = "change_algorithm"
    raise_exception = True
    success_message = "Image validation and upload in progress."

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
    permission_required = "view_algorithmimage"
    raise_exception = True
    queryset = AlgorithmImage.objects.prefetch_related(
        "build__webhook_message"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "image_activate_form": ImageActivateForm(
                    initial={"algorithm_image": self.object.pk},
                    user=self.request.user,
                    algorithm=self.object.algorithm,
                    hide_algorithm_image_input=True,
                )
            }
        )

        return context


class AlgorithmImageImportStatusDetail(
    ObjectPermissionRequiredMixin, DetailView
):
    permission_required = "view_algorithmimage"
    model = AlgorithmImage
    template_name = "components/import_status_detail.html"
    raise_exception = True


class AlgorithmImageBuildStatusDetail(
    ObjectPermissionRequiredMixin, DetailView
):
    permission_required = "view_algorithmimage"
    template_name_suffix = "_build_status_detail"
    model = AlgorithmImage
    raise_exception = True


class AlgorithmImageUpdate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView
):
    model = AlgorithmImage
    form_class = AlgorithmImageUpdateForm
    permission_required = "change_algorithmimage"
    raise_exception = True

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"algorithm": self.object.algorithm})
        return context


class AlgorithmImageActivate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    permission_required = "change_algorithm"
    raise_exception = True
    form_class = ImageActivateForm
    template_name = "algorithms/image_activate.html"

    @cached_property
    def algorithm(self):
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.algorithm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"object": self.algorithm})
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user, "algorithm": self.algorithm})
        return kwargs

    def get_success_message(self, cleaned_data):
        if cleaned_data["algorithm_image"].can_execute:
            return "Image successfully activated."
        else:
            return (
                "Image validation and upload to registry in progress. "
                "It can take a while for this image to become active, "
                "please be patient."
            )

    def form_valid(self, form):
        response = super().form_valid(form=form)

        algorithm_image = form.cleaned_data["algorithm_image"]

        if algorithm_image.can_execute:
            algorithm_image.mark_desired_version()
        else:
            algorithm_image.import_status = ImportStatusChoices.QUEUED
            algorithm_image.save()

            on_commit(
                upload_to_registry_and_sagemaker.signature(
                    kwargs={
                        "app_label": algorithm_image._meta.app_label,
                        "model_name": algorithm_image._meta.model_name,
                        "pk": algorithm_image.pk,
                        "mark_as_desired": True,
                    }
                ).apply_async
            )

        return response

    def get_success_url(self):
        return self.algorithm.get_absolute_url()


class JobCreatePermissionMixin(
    LoginRequiredMixin, VerificationRequiredMixin, AccessMixin
):
    @cached_property
    def algorithm(self) -> Algorithm:
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm(
            "algorithms.execute_algorithm", self.algorithm
        ):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class JobInterfaceSelect(
    JobCreatePermissionMixin,
    FormView,
):
    form_class = JobInterfaceSelectForm
    template_name = "algorithms/job_form_create.html"
    selected_interface = None

    def get(self, request, *args, **kwargs):
        if self.algorithm.interfaces.count() == 1:
            self.selected_interface = self.algorithm.interfaces.get()
            return HttpResponseRedirect(self.get_success_url())
        else:
            return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"algorithm": self.algorithm})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "algorithm": self.algorithm,
                "editors_job_limit": settings.ALGORITHM_IMAGES_COMPLIMENTARY_EDITOR_JOBS,
            }
        )
        return context

    def form_valid(self, form):
        self.selected_interface = form.cleaned_data["algorithm_interface"]
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "algorithms:job-create",
            kwargs={
                "slug": self.algorithm.slug,
                "interface_pk": self.selected_interface.pk,
            },
        )


class JobCreate(
    JobCreatePermissionMixin,
    UserFormKwargsMixin,
    FormView,
):
    form_class = JobCreateForm
    template_name = "algorithms/job_form_create.html"

    @cached_property
    def interface(self):
        return get_object_or_404(
            AlgorithmInterface, pk=self.kwargs["interface_pk"]
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {"algorithm": self.algorithm, "interface": self.interface}
        )
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "algorithm": self.algorithm,
                "editors_job_limit": settings.ALGORITHM_IMAGES_COMPLIMENTARY_EDITOR_JOBS,
            }
        )
        return context

    def form_valid(self, form):
        inputs = form.cleaned_data.pop("additional_inputs")

        algorithm = form.cleaned_data["algorithm_image"].algorithm

        self.object = Job.objects.create(
            **form.cleaned_data,
            time_limit=algorithm.time_limit,
            requires_gpu_type=algorithm.job_requires_gpu_type,
            requires_memory_gb=algorithm.job_requires_memory_gb,
            extra_logs_viewer_groups=[algorithm.editors_group],
            status=Job.VALIDATING_INPUTS,
        )

        try:
            self.object.validate_civ_data_objects_and_execute_linked_task(
                civ_data_objects=inputs, user=self.object.creator
            )
        except CIVNotEditableException as e:
            if self.object.status == self.object.CANCELLED:
                # this can happen for jobs with multiple inputs
                # if one of them fails validation
                pass
            else:
                error_handler = self.object.get_error_handler()
                error_handler.handle_error(
                    error_message="An unexpected error occurred",
                )
                logger.error(e, exc_info=True)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "algorithms:job-progress-detail",
            kwargs={"slug": self.kwargs["slug"], "pk": self.object.pk},
        )


class JobProgressDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    template_name = "algorithms/job_progress_detail.html"
    permission_required = "view_job"
    model = Job
    raise_exception = True

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("algorithm_image__algorithm")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "job_detail_api": reverse(
                    "api:algorithms-job-detail", kwargs={"pk": self.object.pk}
                ),
                "num_image_inputs": self.object.algorithm_interface.inputs.filter(
                    kind__in=InterfaceKinds.image
                ).count(),
                "num_file_inputs": self.object.algorithm_interface.inputs.filter(
                    Q(kind__in=InterfaceKinds.file)
                    | Q(
                        kind__in=InterfaceKinds.json,
                        store_in_database=False,
                    )
                ).count(),
            }
        )
        return context


class JobsList(ViewObjectPermissionListMixin, PaginatedTableListView):
    model = Job
    row_template = "algorithms/job_list_row.html"
    search_fields = [
        "pk",
        "creator__username",
        "inputs__image__name",
        "inputs__image__files__file",
        "comment",
    ]

    columns = [
        Column(title="Detail"),
        Column(title="Created", sort_field="created"),
        Column(title="Creator", sort_field="creator__username"),
        Column(title="Status", sort_field="status"),
        Column(title="Visibility", sort_field="public"),
        Column(title="Comment", sort_field="comment"),
        Column(title="Results"),
        Column(title="Viewer"),
    ]

    default_sort_column = 1

    @cached_property
    def algorithm(self):
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def get_queryset(self):
        queryset = super().get_queryset()
        return (
            queryset.filter(algorithm_image__algorithm=self.algorithm)
            .prefetch_related(
                "outputs__image__files",
                "outputs__interface",
                "inputs__image__files",
                "inputs__interface",
                "viewers__user_set",
            )
            .select_related(
                "creator__user_profile",
                "creator__verification",
                "algorithm_image__algorithm",
            )
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "algorithm": self.algorithm,
            }
        )
        return context


class JobDetail(ObjectPermissionRequiredMixin, DetailView):
    permission_required = "view_job"
    raise_exception = True
    queryset = Job.objects.prefetch_related(
        "outputs__image__files",
        "outputs__interface",
        "inputs__image__files",
        "inputs__interface",
        "viewers__user_set__user_profile",
        "viewers__user_set__verification",
        "viewer_groups",
    ).select_related(
        "creator__user_profile",
        "creator__verification",
        "algorithm_image__algorithm__workstation",
        "job_utilization",
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        viewers_form = ViewersForm()
        viewers_form.fields["action"].initial = ViewersForm.REMOVE

        context.update(
            {
                "viewers_form": viewers_form,
                "job_perms": get_perms(self.request.user, self.object),
            }
        )

        return context


class JobUpdate(LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView):
    model = Job
    form_class = JobForm
    permission_required = "change_job"
    template_name_suffix = "_form_update"
    raise_exception = True


class JobStatusDetail(ObjectPermissionRequiredMixin, DetailView):
    permission_required = "view_job"
    template_name_suffix = "_status_detail"
    model = Job
    raise_exception = True


class DisplaySetFromJobCreate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    FormView,
):
    form_class = DisplaySetFromJobForm
    permission_required = "view_job"
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
    queryset = Algorithm.objects.all().prefetch_related("interfaces")
    serializer_class = AlgorithmSerializer
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ViewObjectPermissionsFilter]
    filterset_fields = ["slug"]


class AlgorithmImageViewSet(ReadOnlyModelViewSet):
    queryset = AlgorithmImage.objects.all()
    serializer_class = AlgorithmImageSerializer
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ViewObjectPermissionsFilter]
    filterset_fields = ["algorithm"]


class JobViewSet(
    CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet
):
    queryset = (
        Job.objects.all()
        .prefetch_related(
            "outputs__interface",
            "inputs__interface",
            "algorithm_image__algorithm__optional_hanging_protocols",
        )
        .select_related(
            "algorithm_image__algorithm__hanging_protocol",
        )
    )
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ViewObjectPermissionsFilter]
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
            return super().form_valid(form)
        except ValidationError as e:
            form.add_error(None, ErrorList(e.messages))
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
    permission_required = "change_algorithm"
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
    permission_required = "change_algorithm"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"algorithm": self.base_object})
        return context


class AlgorithmRepositoryUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    VerificationRequiredMixin,
    GitHubInstallationRequiredMixin,
    UpdateView,
):
    model = Algorithm
    form_class = AlgorithmRepoForm
    template_name = "algorithms/algorithm_repository_update.html"
    permission_required = "change_algorithm"
    raise_exception = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"github_app_install_url": self.github_app_install_url})
        return kwargs


class AlgorithmPublishView(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = Algorithm
    form_class = AlgorithmPublishForm
    permission_required = "change_algorithm"
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


class AlgorithmModelCreate(
    LoginRequiredMixin,
    VerificationRequiredMixin,
    UserFormKwargsMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    CreateView,
):
    model = AlgorithmModel
    form_class = AlgorithmModelForm
    permission_required = "change_algorithm"
    raise_exception = True
    success_message = "Model validation and upload in progress."

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


class AlgorithmModelDetail(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    DetailView,
):
    model = AlgorithmModel
    permission_required = "view_algorithmmodel"
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form_kwargs = {
            "initial": {"algorithm_model": self.object.pk},
            "user": self.request.user,
            "algorithm": self.object.algorithm,
            "hide_algorithm_model_input": True,
        }

        context.update(
            {
                "model_activate_form": AlgorithmModelVersionControlForm(
                    activate=True, **form_kwargs
                ),
                "model_deactivate_form": AlgorithmModelVersionControlForm(
                    activate=False, **form_kwargs
                ),
                "import_status_choices": ImportStatusChoices,
            }
        )

        return context


class AlgorithmModelImportStatusDetail(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    DetailView,
):
    model = AlgorithmModel
    permission_required = "view_algorithmmodel"
    template_name = "components/import_status_detail.html"
    raise_exception = True
    login_url = reverse_lazy("account_login")


class AlgorithmModelUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = AlgorithmModel
    form_class = AlgorithmModelUpdateForm
    permission_required = "change_algorithmmodel"
    raise_exception = True

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"algorithm": self.object.algorithm})
        return context


class AlgorithmModelVersionControl(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    permission_required = "change_algorithm"
    raise_exception = True
    template_name = "algorithms/model_version_control.html"
    form_class = AlgorithmModelVersionControlForm
    activate = None

    def form_valid(self, form):
        response = super().form_valid(form=form)
        algorithm_model = form.cleaned_data["algorithm_model"]
        if self.activate:
            algorithm_model.mark_desired_version()
        else:
            algorithm_model.is_desired_version = False
            algorithm_model.save()
        return response

    @cached_property
    def algorithm(self):
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.algorithm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"object": self.algorithm})
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "user": self.request.user,
                "algorithm": self.algorithm,
                "activate": self.activate,
            }
        )
        return kwargs

    def get_success_message(self, cleaned_data):
        if self.activate:
            return "Model successfully activated."
        else:
            "Model successfully deactivated."

    def get_success_url(self):
        return self.algorithm.get_absolute_url() + "#models"


class AlgorithmImageTemplate(ObjectPermissionRequiredMixin, DetailView):
    model = Algorithm
    permission_required = "change_algorithm"
    raise_exception = True
    queryset = Algorithm.objects.prefetch_related(
        "interfaces__inputs", "interfaces__outputs"
    )

    def get(self, *_, **__):
        algorithm = self.get_object()

        forge_context = get_forge_algorithm_template_context(algorithm)

        buffer = io.BytesIO()
        with ZipFile(buffer, "w") as zipf:
            generate_algorithm_template(
                context=forge_context,
                output_zip_file=zipf,
                target_zpath=Path(""),
            )
        buffer.seek(0)

        return FileResponse(
            streaming_content=buffer,
            as_attachment=True,
            filename=f"{algorithm.slug}-template.zip",
            content_type="application/zip",
        )


class AlgorithmInterfacePermissionMixin(AccessMixin):
    @property
    def algorithm(self):
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def dispatch(self, request, *args, **kwargs):
        if request.user.has_perm(
            "change_algorithm", self.algorithm
        ) and request.user.has_perm("algorithms.add_algorithm"):
            return super().dispatch(request, *args, **kwargs)
        else:
            return self.handle_no_permission()


class AlgorithmInterfaceCreateBase(CreateView):
    model = AlgorithmInterface
    form_class = AlgorithmInterfaceForm
    success_message = "Algorithm interface successfully added"

    def get_success_url(self):
        raise NotImplementedError

    @property
    def base_obj(self):
        raise NotImplementedError

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"base_obj": self.base_obj})
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"base_obj": self.base_obj})
        return kwargs


class AlgorithmInterfaceForAlgorithmCreate(
    AlgorithmInterfacePermissionMixin, AlgorithmInterfaceCreateBase
):
    @property
    def base_obj(self):
        return self.algorithm

    def get_success_url(self):
        return reverse(
            "algorithms:interface-list",
            kwargs={"slug": self.algorithm.slug},
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "algorithm": self.algorithm,
            }
        )
        return context


class AlgorithmInterfacesForAlgorithmList(
    AlgorithmInterfacePermissionMixin, ListView
):
    model = AlgorithmAlgorithmInterface

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(algorithm=self.algorithm)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "algorithm": self.algorithm,
                "interfaces": [obj.interface for obj in self.object_list],
            }
        )
        return context


class AlgorithmInterfaceForAlgorithmDelete(
    AlgorithmInterfacePermissionMixin, DeleteView
):
    model = AlgorithmAlgorithmInterface

    @property
    def algorithm_interface(self):
        return get_object_or_404(
            klass=AlgorithmAlgorithmInterface,
            algorithm=self.algorithm,
            interface__pk=self.kwargs["interface_pk"],
        )

    def get_object(self, queryset=None):
        return self.algorithm_interface

    def get_success_url(self):
        return reverse(
            "algorithms:interface-list",
            kwargs={"slug": self.algorithm.slug},
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "algorithm": self.algorithm,
            }
        )
        return context
