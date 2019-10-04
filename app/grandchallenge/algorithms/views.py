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
from rest_framework.viewsets import ReadOnlyModelViewSet, GenericViewSet

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
)
from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
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


class AlgorithmImageCreate(UserIsStaffMixin, CreateView):
    model = AlgorithmImage
    form_class = AlgorithmImageForm

    @property
    def algorithm(self):
        return Algorithm.objects.get(slug=self.kwargs["slug"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.algorithm = self.algorithm

        uploaded_file = form.cleaned_data["chunked_upload"][0]
        form.instance.staged_image_uuid = uploaded_file.uuid

        return super().form_valid(form)


class AlgorithmImageDetail(UserIsStaffMixin, DetailView):
    model = AlgorithmImage


class AlgorithmExecutionSessionCreate(
    UserIsStaffMixin, SuccessMessageMixin, CreateView
):
    model = RawImageUploadSession
    form_class = UploadRawImagesForm
    template_name = "algorithms/algorithm_execution_session_create.html"
    success_message = (
        "Your images have been uploaded, "
        "please check back here to see the processing status."
    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.algorithm_image = AlgorithmImage.objects.get(
            slug=self.kwargs["slug"]
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "algorithms:image-detail", kwargs={"slug": self.kwargs["slug"]}
        )


class AlgorithmImageViewSet(ReadOnlyModelViewSet):
    queryset = AlgorithmImage.objects.all()
    serializer_class = AlgorithmImageSerializer


class ResultViewSet(ReadOnlyModelViewSet):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer


class JobViewSet(
    CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet
):
    serializer_class = JobSerializer
    queryset = Job.objects.all()
