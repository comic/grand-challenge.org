import logging

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from rest_framework.mixins import (
    CreateModelMixin,
    RetrieveModelMixin,
    ListModelMixin,
)
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.viewsets import ReadOnlyModelViewSet, GenericViewSet
from rest_framework_guardian.filters import DjangoObjectPermissionsFilter

from grandchallenge.algorithms.forms import AlgorithmImageForm, AlgorithmForm
from grandchallenge.algorithms.models import (
    AlgorithmImage,
    Job,
    Result,
    Algorithm,
)
from grandchallenge.algorithms.serializers import (
    AlgorithmImageSerializer,
    ResultSerializer,
    JobSerializer,
    AlgorithmSerializer,
)
from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.subdomains.utils import reverse

logger = logging.getLogger(__name__)


class AlgorithmCreate(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Algorithm
    form_class = AlgorithmForm
    permission_required = (
        f"{Algorithm._meta.app_label}.add_{Algorithm._meta.model_name}"
    )

    def form_valid(self, form):
        response = super().form_valid(form=form)
        self.object.add_editor(self.request.user)
        return response


class AlgorithmList(LoginRequiredMixin, PermissionListMixin, ListView):
    model = Algorithm
    permission_required = {
        f"{Algorithm._meta.app_label}.view_{Algorithm._meta.model_name}"
    }


class AlgorithmDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = Algorithm
    permission_required = (
        f"{Algorithm._meta.app_label}.view_{Algorithm._meta.model_name}"
    )
    raise_exception = True


class AlgorithmUpdate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView
):
    model = Algorithm
    form_class = AlgorithmForm
    permission_required = (
        f"{Algorithm._meta.app_label}.change_{Algorithm._meta.model_name}"
    )
    raise_exception = True


class AlgorithmImageCreate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, CreateView
):
    model = AlgorithmImage
    form_class = AlgorithmImageForm
    permission_required = (
        f"{Algorithm._meta.app_label}.change_{Algorithm._meta.model_name}"
    )
    raise_exception = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    @property
    def algorithm(self):
        return Algorithm.objects.get(slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.algorithm

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.algorithm = self.algorithm

        uploaded_file = form.cleaned_data["chunked_upload"][0]
        form.instance.staged_image_uuid = uploaded_file.uuid

        return super().form_valid(form)


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
    fields = ("requires_gpu",)
    permission_required = f"{AlgorithmImage._meta.app_label}.change_{AlgorithmImage._meta.model_name}"
    raise_exception = True


class AlgorithmExecutionSessionCreate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    CreateView,
):
    model = RawImageUploadSession
    form_class = UploadRawImagesForm
    template_name = "algorithms/algorithm_execution_session_create.html"
    success_message = (
        "Your images have been uploaded, "
        "please check back here to see the processing status."
    )
    permission_required = (
        f"{Algorithm._meta.app_label}.view_{Algorithm._meta.model_name}"
    )
    raise_exception = True

    @property
    def algorithm(self) -> Algorithm:
        return Algorithm.objects.get(slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.algorithm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.algorithm_image = self.algorithm.latest_ready_image
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "algorithms:image-detail", kwargs={"slug": self.kwargs["slug"]}
        )


class AlgorithmViewSet(ReadOnlyModelViewSet):
    queryset = Algorithm.objects.all()
    serializer_class = AlgorithmSerializer
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoObjectPermissionsFilter]


class AlgorithmImageViewSet(ReadOnlyModelViewSet):
    queryset = AlgorithmImage.objects.all()
    serializer_class = AlgorithmImageSerializer
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoObjectPermissionsFilter]


class ResultViewSet(ReadOnlyModelViewSet):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer


class JobViewSet(
    CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet
):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
