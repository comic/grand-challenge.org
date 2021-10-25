import logging
from datetime import timedelta
from typing import Dict

import requests
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    PermissionDenied,
    ValidationError,
)
from django.forms.utils import ErrorList
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
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
    AlgorithmForm,
    AlgorithmImageForm,
    AlgorithmImageUpdateForm,
    AlgorithmInputsForm,
    AlgorithmPermissionRequestUpdateForm,
    AlgorithmRepoForm,
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
from grandchallenge.codebuild.models import Build
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKind,
)
from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.forms import UserFormKwargsMixin
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


class ComponentInterfaceList(LoginRequiredMixin, ListView):
    model = ComponentInterface


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
    ordering = "-created"
    filter_class = AlgorithmFilter
    paginate_by = 40

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related("publications",)
            .order_by("-created")
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
                    random_encode("mailto:support@grand-challenge.org"),
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
        "algorithm_container_images__build__webhook_message"
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

        pending_permission_requests = AlgorithmPermissionRequest.objects.filter(
            algorithm=context["object"],
            status=AlgorithmPermissionRequest.PENDING,
        ).count()
        context.update(
            {
                "pending_permission_requests": pending_permission_requests,
                "github_app_install_url": f"{settings.GITHUB_APP_INSTALL_URL}?state={self.object.slug}",
                "builds": Build.objects.filter(
                    algorithm_image__algorithm=self.object
                ),
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
    form_class = AlgorithmForm
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


class UsersUpdate(AlgorithmUserGroupUpdateMixin):
    form_class = UsersForm
    success_message = "Users successfully updated"


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

    def get_remaining_jobs(self, *, credits_per_job: int) -> Dict:
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
                        "algorithm_image_pk": self.algorithm.latest_ready_image.pk
                    },
                    immutable=True,
                )
            }
        )
        return kwargs

    def get_permission_object(self):
        return self.algorithm

    def get_initial(self):
        if self.algorithm.latest_ready_image is None:
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
            algorithm_image=self.algorithm.latest_ready_image,
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
            if ci.kind in InterfaceKind.interface_type_image():
                if value:
                    # create civ without image, image will be added when import completes
                    civ = ComponentInterfaceValue.objects.create(interface=ci)
                    civs.append(civ)
                    upload_pks[civ.pk] = create_upload(value)
            elif ci.kind in InterfaceKind.interface_type_file():
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


class JobsList(PermissionListMixin, PaginatedTableListView):
    model = Job
    permission_required = "algorithms.view_job"
    row_template = "algorithms/job_list_row.html"
    search_fields = [
        "pk",
        "creator__username",
        "inputs__image__name",
        "inputs__image__files__file",
        "comment",
    ]
    columns = [
        Column(title="Details", sort_field="pk"),
        Column(title="Created", sort_field="created"),
        Column(title="Creator", sort_field="creator__username"),
        Column(title="Result", sort_field="inputs__image__name"),
        Column(title="Comment", sort_field="comment"),
        Column(title="Visibility", sort_field="public"),
        Column(title="Viewer", sort_field="inputs__image__files__file"),
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
        context.update({"algorithm": self.algorithm})
        return context


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
    permission_required = "algorithms.change_job"
    raise_exception = True


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
        .select_related("algorithm_image__algorithm")
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

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()

        user_token = get_object_or_404(GitHubUserToken, user=self.request.user)

        if user_token.access_token_is_expired:
            user_token.refresh_access_token()
            user_token.save()

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {user_token.access_token}",
        }

        installations = requests.get(
            "https://api.github.com/user/installations",
            headers=headers,
            timeout=5,
        ).json()

        repos = []
        for installation in installations.get("installations", []):
            response = requests.get(
                f"https://api.github.com/user/installations/{installation['id']}/repositories",
                headers=headers,
                timeout=5,
            ).json()

            repos += [repo["full_name"] for repo in response["repositories"]]

        kwargs.update({"repos": repos})
        return kwargs
