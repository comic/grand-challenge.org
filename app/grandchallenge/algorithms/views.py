import logging

from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    PermissionDenied,
    ValidationError,
)
from django.forms.utils import ErrorList
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)
from django_filters.rest_framework import DjangoFilterBackend
from guardian.core import ObjectPermissionChecker
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.algorithms.forms import (
    AlgorithmForm,
    AlgorithmImageForm,
    AlgorithmImageUpdateForm,
    AlgorithmPermissionRequestUpdateForm,
    EditorsForm,
    ResultForm,
    UsersForm,
)
from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmPermissionRequest,
    Job,
    Result,
)
from grandchallenge.algorithms.serializers import (
    AlgorithmImageSerializer,
    AlgorithmSerializer,
    JobSerializer,
    ResultSerializer,
)
from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.core.forms import UserFormKwargsMixin
from grandchallenge.core.permissions.mixins import UserIsNotAnonMixin
from grandchallenge.core.views import (
    PaginatedTableListView,
    PermissionRequestUpdate,
)
from grandchallenge.subdomains.utils import reverse

logger = logging.getLogger(__name__)


class AlgorithmCreate(
    UserFormKwargsMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = Algorithm
    form_class = AlgorithmForm
    permission_required = (
        f"{Algorithm._meta.app_label}.add_{Algorithm._meta.model_name}"
    )

    def form_valid(self, form):
        response = super().form_valid(form=form)
        self.object.add_editor(self.request.user)
        return response


class AlgorithmList(PermissionListMixin, ListView):
    model = Algorithm
    permission_required = {
        f"{Algorithm._meta.app_label}.view_{Algorithm._meta.model_name}"
    }
    ordering = "-created"


class AlgorithmDetail(ObjectPermissionRequiredMixin, DetailView):
    model = Algorithm
    permission_required = (
        f"{Algorithm._meta.app_label}.view_{Algorithm._meta.model_name}"
    )
    raise_exception = True

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
        context.update({"form": form})

        pending_permission_requests = AlgorithmPermissionRequest.objects.filter(
            algorithm=context["object"],
            status=AlgorithmPermissionRequest.PENDING,
        ).count()
        context.update(
            {"pending_permission_requests": pending_permission_requests}
        )

        context.update(
            {
                "average_job_duration": Job.objects.filter(
                    algorithm_image__algorithm=context["object"],
                    status=Job.SUCCESS,
                ).average_duration()
            }
        )

        return context


class AlgorithmUpdate(
    UserFormKwargsMixin,
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = Algorithm
    form_class = AlgorithmForm
    permission_required = (
        f"{Algorithm._meta.app_label}.change_{Algorithm._meta.model_name}"
    )
    raise_exception = True


class AlgorithmUserAutocomplete(
    LoginRequiredMixin, UserPassesTestMixin, autocomplete.Select2QuerySetView
):
    def test_func(self):
        group_pks = (
            Algorithm.objects.all()
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


class AlgorithmUserGroupUpdateMixin(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    template_name = "algorithms/algorithm_user_groups_form.html"
    permission_required = (
        f"{Algorithm._meta.app_label}.change_{Algorithm._meta.model_name}"
    )
    raise_exception = True

    def get_permission_object(self):
        return self.algorithm

    @property
    def algorithm(self):
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {"object": self.algorithm, "role": self.get_form().role}
        )
        return context

    def get_success_url(self):
        return self.algorithm.get_absolute_url()

    def form_valid(self, form):
        form.add_or_remove_user(algorithm=self.algorithm)
        return super().form_valid(form)


class EditorsUpdate(AlgorithmUserGroupUpdateMixin):
    form_class = EditorsForm
    success_message = "Editors successfully updated"


class UsersUpdate(AlgorithmUserGroupUpdateMixin):
    form_class = UsersForm
    success_message = "Users successfully updated"


class AlgorithmImageCreate(
    UserFormKwargsMixin,
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    CreateView,
):
    model = AlgorithmImage
    form_class = AlgorithmImageForm
    permission_required = (
        f"{Algorithm._meta.app_label}.change_{Algorithm._meta.model_name}"
    )
    raise_exception = True

    @property
    def algorithm(self):
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.algorithm

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.algorithm = self.algorithm

        uploaded_file = form.cleaned_data["chunked_upload"][0]
        form.instance.staged_image_uuid = uploaded_file.uuid

        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"algorithm": self.algorithm})
        return context


class AlgorithmImageDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = AlgorithmImage
    permission_required = f"{AlgorithmImage._meta.app_label}.view_{AlgorithmImage._meta.model_name}"
    raise_exception = True


class AlgorithmImageUpdate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView
):
    model = AlgorithmImage
    form_class = AlgorithmImageUpdateForm
    permission_required = f"{AlgorithmImage._meta.app_label}.change_{AlgorithmImage._meta.model_name}"
    raise_exception = True

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"algorithm": self.object.algorithm})
        return context


class AlgorithmExecutionSessionCreate(
    UserFormKwargsMixin,
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    CreateView,
):
    model = RawImageUploadSession
    form_class = UploadRawImagesForm
    template_name = "algorithms/algorithm_execution_session_create.html"
    permission_required = (
        f"{Algorithm._meta.app_label}.execute_{Algorithm._meta.model_name}"
    )
    raise_exception = True

    @property
    def algorithm(self) -> Algorithm:
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.algorithm

    def get_initial(self):
        if self.algorithm.latest_ready_image is None:
            raise Http404()
        return super().get_initial()

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.algorithm_image = self.algorithm.latest_ready_image
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"algorithm": self.algorithm})
        return context

    def get_success_url(self):
        return reverse(
            "algorithms:execution-session-detail",
            kwargs={"slug": self.kwargs["slug"], "pk": self.object.pk},
        )


class AlgorithmExecutionSessionList(
    LoginRequiredMixin, PermissionListMixin, ListView
):
    model = RawImageUploadSession
    template_name = "algorithms/executionsession_list.html"
    permission_required = "cases.view_rawimageuploadsession"
    raise_exception = True

    @cached_property
    def algorithm(self):
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"algorithm": self.algorithm})
        return context

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        return (
            qs.filter(algorithm_image__algorithm=self.algorithm)
            .prefetch_related("image_set__job_set")
            .select_related("creator__user_profile")
        )


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
                "average_job_duration": Job.objects.filter(
                    algorithm_image__algorithm=self.algorithm,
                    status=Job.SUCCESS,
                ).average_duration(),
            }
        )
        return context


class AlgorithmResultsList(PermissionListMixin, PaginatedTableListView):
    model = Result
    permission_required = (
        f"{Result._meta.app_label}.view_{Result._meta.model_name}"
    )
    row_template = "algorithms/data_tables/result_list.html"
    search_fields = [
        "job__creator__username",
        "job__image__name",
        "images__files__file",
        "comment",
    ]
    columns = [
        "job__created",
        "job__creator__username",
        "job__image__name",
        "public",
        "images__files__file",
        "comment",
    ]
    order_by = "job__created"

    def get_row_context(self, result, *args, checker, **kwargs):
        return {
            "result": result,
            "algorithm": self.algorithm,
            "change_result": checker.has_perm("change_result", result),
        }

    def get_data(self, results, *args, **kwargs):
        checker = ObjectPermissionChecker(self.request.user)
        checker.prefetch_perms(results)
        return [
            self.render_row_data(result, checker=checker) for result in results
        ]

    @cached_property
    def algorithm(self):
        return get_object_or_404(Algorithm, slug=self.kwargs["slug"])

    def get_unfiltered_queryset(self):
        queryset = self.object_list
        return (
            queryset.filter(job__algorithm_image__algorithm=self.algorithm)
            .prefetch_related("images__files", "job__image__files")
            .select_related("job__creator__user_profile")
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"algorithm": self.algorithm})

        return context


class AlgorithmResultUpdate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView
):
    model = Result
    form_class = ResultForm
    permission_required = (
        f"{Result._meta.app_label}.change_{Result._meta.model_name}"
    )
    raise_exception = True

    def get_success_url(self):
        return reverse(
            "algorithms:results-list",
            kwargs={"slug": self.object.job.algorithm_image.algorithm.slug},
        )


class AlgorithmViewSet(ReadOnlyModelViewSet):
    queryset = Algorithm.objects.all()
    serializer_class = AlgorithmSerializer
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [ObjectPermissionsFilter]


class AlgorithmImageViewSet(ReadOnlyModelViewSet):
    queryset = AlgorithmImage.objects.all()
    serializer_class = AlgorithmImageSerializer
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]
    filterset_fields = ["algorithm"]


class JobViewSet(ReadOnlyModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]
    filterset_fields = ["algorithm_image__algorithm", "image"]


class ResultViewSet(ReadOnlyModelViewSet):
    queryset = Result.objects.all().prefetch_related("job")
    serializer_class = ResultSerializer
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]
    filterset_fields = ["job__algorithm_image__algorithm", "job__image"]


class AlgorithmPermissionRequestCreate(
    UserIsNotAnonMixin, SuccessMessageMixin, CreateView
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
    permission_required = (
        f"{Algorithm._meta.app_label}.change_{Algorithm._meta.model_name}"
    )
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
            .select_related("user__user_profile")
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
    permission_required = (
        f"{Algorithm._meta.app_label}.change_{Algorithm._meta.model_name}"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"algorithm": self.base_object})
        return context
