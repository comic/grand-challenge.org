from django.core.files import File
from django.views.generic import CreateView, ListView, DetailView, TemplateView

from comicmodels.models import ComicSite
from comicsite.permissions.mixins import UserIsChallengeAdminMixin, \
    UserIsChallengeParticipantOrAdminMixin
from evaluation.forms import MethodForm
from evaluation.models import Result, Submission, Job, Method
from jqfileupload.widgets.uploader import AjaxUploadWidget


class EvaluationManage(UserIsChallengeAdminMixin, TemplateView):
    template_name = "evaluation/manage.html"


class MethodCreate(UserIsChallengeAdminMixin, CreateView):
    model = Method
    form_class = MethodForm

    def get_context_data(self, **kwargs):
        context = super(MethodCreate, self).get_context_data(**kwargs)
        context["upload_widget"] = AjaxUploadWidget.TEMPLATE_ATTRS
        return context

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.challenge = ComicSite.objects.get(
            pk=self.request.project_pk)

        uploaded_file = form.cleaned_data['chunked_upload'][0]
        with uploaded_file.open() as f:
            form.instance.image.save(uploaded_file.name, File(f))

        return super(MethodCreate, self).form_valid(form)


class MethodList(UserIsChallengeAdminMixin, ListView):
    model = Method

    def get_queryset(self):
        queryset = super(MethodList, self).get_queryset()
        return queryset.filter(challenge__pk=self.request.project_pk)


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

    def get_queryset(self):
        queryset = super(SubmissionList, self).get_queryset()
        return queryset.filter(challenge__pk=self.request.project_pk)


class SubmissionDetail(UserIsChallengeAdminMixin, DetailView):
    # TODO - if participant: list only their submissions
    model = Submission


class JobCreate(UserIsChallengeAdminMixin, CreateView):
    model = Job
    fields = '__all__'


class JobList(UserIsChallengeAdminMixin, ListView):
    # TODO - if participant: list only their jobs
    model = Job

    def get_queryset(self):
        queryset = super(JobList, self).get_queryset()
        return queryset.filter(challenge__pk=self.request.project_pk)


class JobDetail(UserIsChallengeAdminMixin, DetailView):
    # TODO - if participant: list only their jobs
    model = Job


class ResultList(ListView):
    model = Result

    def get_queryset(self):
        queryset = super(ResultList, self).get_queryset()
        return queryset.filter(challenge__pk=self.request.project_pk)


class ResultDetail(DetailView):
    model = Result
