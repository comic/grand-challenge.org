from django.views.generic import ListView, CreateView, DetailView

from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.reader_studies.forms import ReaderStudyCreateForm
from grandchallenge.reader_studies.models import ReaderStudy


class ReaderStudyList(ListView):
    model = ReaderStudy


class ReaderStudyCreate(UserIsStaffMixin, CreateView):
    model = ReaderStudy
    form_class = ReaderStudyCreateForm

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super().form_valid(form)


class ReaderStudyDetail(DetailView):
    model = ReaderStudy


class AddImagesToReaderStudy(CreateView):
    model = RawImageUploadSession
    form_class = UploadRawImagesForm
    template_name = "reader_studies/readerstudy_add_images.html"

    @property
    def readerstudy(self):
        return ReaderStudy.objects.get(slug=self.kwargs["slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"object": self.readerstudy})
        return context

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.readerstudy = self.readerstudy
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.readerstudy.get_absolute_url()
