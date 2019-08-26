import logging

from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, CreateView, DetailView

from grandchallenge.algorithms.forms import AlgorithmImageForm
from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.subdomains.utils import reverse
from grandchallenge.algorithms.serializers import (
    AlgorithmImageSerializer,
    ResultSerializer,
    JobSerializer,
)
from grandchallenge.algorithms.models import AlgorithmImage, Job, Result

from rest_framework.viewsets import ReadOnlyModelViewSet, GenericViewSet
from rest_framework.mixins import (
    CreateModelMixin,
    RetrieveModelMixin,
    ListModelMixin,
)

logger = logging.getLogger(__name__)


class AlgorithmImageList(UserIsStaffMixin, ListView):
    model = AlgorithmImage


class AlgorithmImageCreate(UserIsStaffMixin, CreateView):
    model = AlgorithmImage
    form_class = AlgorithmImageForm

    def form_valid(self, form):
        form.instance.creator = self.request.user
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

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.algorithm = AlgorithmImage.objects.get(
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
