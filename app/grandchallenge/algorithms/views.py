import logging

from django.contrib.messages.views import SuccessMessageMixin
from django.core.files import File
from django.views.generic import ListView, CreateView, DetailView
from nbconvert import HTMLExporter

from grandchallenge.algorithms.forms import AlgorithmForm
from grandchallenge.algorithms.models import Algorithm
from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.subdomains.utils import reverse

logger = logging.getLogger(__name__)


class AlgorithmList(UserIsStaffMixin, ListView):
    model = Algorithm


def ipynb_to_html(*, notebook: File):
    # Run nbconvert on the description and get the html on each save
    html_exporter = HTMLExporter()
    html_exporter.template_file = "full"

    with notebook.open() as d:
        (body, _) = html_exporter.from_file(d)

    return body


class AlgorithmCreate(UserIsStaffMixin, CreateView):
    model = Algorithm
    form_class = AlgorithmForm

    def form_valid(self, form):
        form.instance.creator = self.request.user

        try:
            form.instance.description_html = ipynb_to_html(
                notebook=form.cleaned_data["ipython_notebook"]
            )
        except AttributeError:
            logger.warning("Could not convert notebook to html.")

        uploaded_file = form.cleaned_data["chunked_upload"][0]
        form.instance.staged_image_uuid = uploaded_file.uuid

        return super().form_valid(form)


class AlgorithmDetail(UserIsStaffMixin, DetailView):
    model = Algorithm


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
        form.instance.algorithm = Algorithm.objects.get(
            slug=self.kwargs["slug"]
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "algorithms:detail", kwargs={"slug": self.kwargs["slug"]}
        )
