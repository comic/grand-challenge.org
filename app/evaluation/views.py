from auth_mixins import LoginRequiredMixin
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.generic import CreateView, ListView, DetailView, TemplateView
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet

from comicmodels.models import ComicSite
from comicsite.permissions.mixins import UserIsChallengeAdminMixin
from evaluation.forms import UploadForm
from evaluation.models import Result, Submission, Job, Method
from evaluation.serializers import ResultSerializer, SubmissionSerializer, \
    JobSerializer, MethodSerializer
from evaluation.widgets.uploader import AjaxUploadWidget


class ResultViewSet(ModelViewSet):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


class SubmissionViewSet(ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    parser_classes = (MultiPartParser, FormParser,)
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def perform_create(self, serializer):
        # Validate that the challenge exists
        try:
            short_name = self.request.data.get('challenge')
            challenge = ComicSite.objects.get(
                short_name=short_name)
        except ComicSite.DoesNotExist:
            raise ValidationError(
                f"Challenge {short_name} does not exist.")

        serializer.save(user=self.request.user,
                        challenge=challenge,
                        file=self.request.data.get('file'))


class JobViewSet(ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


class MethodViewSet(ModelViewSet):
    queryset = Method.objects.all()
    serializer_class = MethodSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


class EvaluationAdmin(UserIsChallengeAdminMixin, TemplateView):
    # TODO: Challenge Admin Only
    template_name = "evaluation/admin.html"


class MethodCreate(CreateView):
    # TODO: Challenge Admin Only
    model = Method
    fields = '__all__'


class MethodList(ListView):
    # TODO: Challenge Admin Only
    model = Method


class MethodDetail(DetailView):
    # TODO: Challenge Admin Only
    model = Method


class SubmissionCreate(CreateView):
    # TODO: Challenge Participant Only
    model = Submission
    fields = '__all__'


class SubmissionList(ListView):
    # TODO: Challenge Admin Only
    model = Submission


class SubmissionDetail(DetailView):
    # TODO: Challenge Admin Only
    model = Submission


class JobCreate(CreateView):
    # TODO: Challenge Admin Only
    model = Job
    fields = '__all__'


class JobList(ListView):
    # TODO: Challenge Admin Only
    model = Job


class JobDetail(DetailView):
    # TODO: Challenge Admin Only
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
