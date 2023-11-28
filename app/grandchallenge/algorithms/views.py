import logging

from django.contrib import messages
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import OuterRef, Subquery
from django.forms.utils import ErrorList
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
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
from guardian.shortcuts import get_perms
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
    AlgorithmPermissionRequestUpdateForm,
    AlgorithmPublishForm,
    AlgorithmRepoForm,
    AlgorithmUpdateForm,
    DisplaySetFromJobForm,
    ImageActivateForm,
    JobCreateForm,
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
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.cases.widgets import WidgetChoices
from grandchallenge.components.models import (
    ComponentInterfaceValue,
    ImportStatusChoices,
    InterfaceKind,
)
from grandchallenge.components.tasks import upload_to_registry_and_sagemaker
from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.forms import UserFormKwargsMixin
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    PermissionListMixin,
    filter_by_permission,
)
from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.core.views import PermissionRequestUpdate
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.github.views import GitHubInstallationRequiredMixin
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
        "optional_hanging_protocols",
    )

    def on_permission_check_fail(self, request, response, obj=None):
        response = self.get(request)
        return response

    def check_permissions(self, request):
        """Checks if *request.user* has all permissions returned by *get_required_permissions* method.

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

        pending_permission_requests = (
            AlgorithmPermissionRequest.objects.filter(
                algorithm=context["object"],
                status=AlgorithmPermissionRequest.PENDING,
            ).count()
        )

        context.update(
            {
                "form": form,
                "editor_remove_form": editor_remove_form,
                "pending_permission_requests": pending_permission_requests,
                "algorithm_perms": get_perms(self.request.user, self.object),
            }
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        # Only users with the add_algorithm permission can change
        # the input and output interfaces, other users must use
        # the interfaces pre-set by the Phase
        kwargs.update(
            {
                "interfaces_editable": self.request.user.has_perm(
                    "algorithms.add_algorithm"
                )
            }
        )

        return kwargs


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
    SuccessMessageMixin,
    CreateView,
):
    model = AlgorithmImage
    form_class = AlgorithmImageForm
    permission_required = "algorithms.change_algorithm"
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
    permission_required = "algorithms.view_algorithmimage"
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


class AlgorithmImageActivate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    permission_required = "algorithms.change_algorithm"
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

            upload_to_registry_and_sagemaker.signature(
                kwargs={
                    "app_label": algorithm_image._meta.app_label,
                    "model_name": algorithm_image._meta.model_name,
                    "pk": algorithm_image.pk,
                    "mark_as_desired": True,
                }
            ).apply_async()

        return response

    def get_success_url(self):
        return self.algorithm.get_absolute_url()


class JobCreate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UserFormKwargsMixin,
    FormView,
):
    form_class = JobCreateForm
    template_name = "algorithms/job_form_create.html"
    permission_required = "algorithms.execute_algorithm"
    raise_exception = True

    @cached_property
    def algorithm(self) -> Algorithm:
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

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
        return context

    def form_valid(self, form):
        def create_upload_session(image_files):
            upload_session = RawImageUploadSession.objects.create(
                creator=self.request.user
            )
            upload_session.user_uploads.set(image_files)
            return upload_session.pk

        component_interface_values = []
        upload_session_pks = {}

        interfaces = {ci.slug: ci for ci in self.algorithm.inputs.all()}

        for slug, value in form.cleaned_data.items():
            if slug == "algorithm_image":
                continue

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
                        component_interface_values.append(civ)
                    elif widget == WidgetChoices.IMAGE_UPLOAD:
                        # create civ without image, image will be added when import completes
                        civ = ComponentInterfaceValue.objects.create(
                            interface=ci
                        )
                        component_interface_values.append(civ)
                        upload_session_pks[civ.pk] = create_upload_session(
                            value
                        )
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
                component_interface_values.append(civ)
            else:
                civ = ci.create_instance(value=value)
                component_interface_values.append(civ)

        job = Job.objects.create(
            creator=self.request.user,
            algorithm_image=form.cleaned_data["algorithm_image"],
            extra_logs_viewer_groups=[self.algorithm.editors_group],
            input_civ_set=component_interface_values,
            time_limit=self.algorithm.time_limit,
        )
        job.sort_inputs_and_execute(upload_session_pks=upload_session_pks)

        return HttpResponseRedirect(
            reverse(
                "algorithms:job-progress-detail",
                kwargs={"slug": self.kwargs["slug"], "pk": job.pk},
            )
        )


class JobProgressDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    template_name = "algorithms/job_progress_detail.html"
    permission_required = "algorithms.view_job"
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
                )
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
            elif (
                interface.kind
                in {
                    InterfaceKind.InterfaceKindChoices.STRING,
                    InterfaceKind.InterfaceKindChoices.INTEGER,
                    InterfaceKind.InterfaceKindChoices.FLOAT,
                    InterfaceKind.InterfaceKindChoices.BOOL,
                }
                and interface.store_in_database
            ):
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
        json = []
        for output in self.object.outputs.all():
            if (
                output.interface.kind
                == InterfaceKind.InterfaceKindChoices.CHART
            ):
                charts.append(output)
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
            elif (
                output.interface.kind
                in [
                    InterfaceKind.InterfaceKindChoices.BOOL,
                    InterfaceKind.InterfaceKindChoices.FLOAT,
                    InterfaceKind.InterfaceKindChoices.INTEGER,
                    InterfaceKind.InterfaceKindChoices.STRING,
                ]
                and output.interface.store_in_database
            ):
                json.append(output)

        context.update(
            {
                "viewers_form": viewers_form,
                "job_perms": get_perms(self.request.user, self.object),
                "charts": charts,
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
    template_name_suffix = "_form_update"
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
    permission_required = "algorithms.change_algorithm"
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
