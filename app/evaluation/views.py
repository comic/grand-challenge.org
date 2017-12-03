from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.generic import CreateView, ListView, DetailView, TemplateView

from comicmodels.models import ComicSite
from comicsite.permissions.mixins import UserIsChallengeAdminMixin, \
    UserIsChallengeParticipantOrAdminMixin
from evaluation.forms import UploadForm
from evaluation.models import Result, Submission, Job, Method
from evaluation.widgets.uploader import AjaxUploadWidget


class EvaluationAdmin(UserIsChallengeAdminMixin, TemplateView):
    template_name = "evaluation/admin.html"


class MethodCreate(UserIsChallengeAdminMixin, CreateView):
    model = Method
    fields = ['image']

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.challenge = ComicSite.objects.get(
            pk=self.request.project_pk)
        return super(MethodCreate, self).form_valid(form)


class MethodList(UserIsChallengeAdminMixin, ListView):
    model = Method


class MethodDetail(UserIsChallengeAdminMixin, DetailView):
    model = Method


class SubmissionCreate(UserIsChallengeParticipantOrAdminMixin, CreateView):
    model = Submission
    fields = ['file']

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.challenge = ComicSite.objects.get(
            pk=self.request.project_pk)
        return super(SubmissionCreate,self).form_valid(form)


class SubmissionList(UserIsChallengeAdminMixin, ListView):
    # TODO - if participant: list only their submissions
    model = Submission


class SubmissionDetail(UserIsChallengeAdminMixin, DetailView):
    # TODO - if participant: list only their submissions
    model = Submission


class JobCreate(UserIsChallengeAdminMixin, CreateView):
    model = Job
    fields = '__all__'


class JobList(UserIsChallengeAdminMixin, ListView):
    # TODO - if participant: list only their jobs
    model = Job


class JobDetail(UserIsChallengeAdminMixin, DetailView):
    # TODO - if participant: list only their jobs
    model = Job


class ResultList(ListView):
    model = Result


class ResultDetail(DetailView):
    model = Result


def uploader_widget_test(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        test_form = UploadForm(request.POST)
        if test_form.is_valid():
            result = "Success!!!\n"
            result += "\n".join(
                f"  {k}: {v}" for k, v in test_form.cleaned_data.items())

            result += "\n\n"

            f1 = test_form.cleaned_data["upload_form"][0]
            with f1.open() as f:
                the_bytes = f.read(16)
            result += f"""
You uploaded {len(test_form.cleaned_data["upload_form"])} files in the first form.

The first 16 bytes of the first file were: {the_bytes}
            """
        else:
            result = "Validation error:\n"
            result += "\n".join(f"  {e}" for e in test_form.errors)
        return HttpResponse(result, content_type="text/plain")
    else:
        test_form = UploadForm()
        return render(request, "uploader_widget_test.html", {
            "testform": test_form,
            "upload_widget": AjaxUploadWidget.TEMPLATE_ATTRS
        })
