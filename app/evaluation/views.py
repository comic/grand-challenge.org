from datetime import timedelta

from django.contrib.messages.views import SuccessMessageMixin
from django.core.files import File
from django.db.models import Q
from django.utils import timezone
from django.views.generic import (
    CreateView,
    ListView,
    DetailView,
    TemplateView,
    UpdateView,
)

from comicmodels.models import ComicSite
from comicsite.core.urlresolvers import reverse
from comicsite.permissions.mixins import (
    UserIsChallengeAdminMixin,
    UserIsChallengeParticipantOrAdminMixin,
)
from evaluation.forms import MethodForm, SubmissionForm
from evaluation.models import Result, Submission, Job, Method, Config


class EvaluationManage(UserIsChallengeAdminMixin, TemplateView):
    template_name = "evaluation/manage.html"


class ConfigUpdate(UserIsChallengeAdminMixin, SuccessMessageMixin, UpdateView):
    model = Config
    fields = (
        'use_teams',
        'daily_submission_limit',
        'score_title',
        'score_jsonpath',
        'score_default_sort',
        'extra_results_columns',
        'allow_submission_comments',
        'allow_supplementary_file',
        'require_supplementary_file',
        'supplementary_file_label',
        'supplementary_file_help_text',
        'show_supplementary_file_link',
    )
    success_message = "Configuration successfully updated"

    def get_object(self, queryset=None):
        challenge = ComicSite.objects.get(pk=self.request.project_pk)
        return challenge.evaluation_config


class MethodCreate(UserIsChallengeAdminMixin, CreateView):
    model = Method
    form_class = MethodForm

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


class SubmissionCreate(UserIsChallengeParticipantOrAdminMixin,
                       SuccessMessageMixin, CreateView):
    model = Submission
    form_class = SubmissionForm
    success_message = (
        "Your submission was successful. "
        "Please keep checking this page for your result."
    )

    def get_form_kwargs(self):
        kwargs = super(SubmissionCreate, self).get_form_kwargs()

        config = Config.objects.get(challenge__pk=self.request.project_pk)

        kwargs.update({
            'display_comment_field': config.allow_submission_comments,
            'allow_supplementary_file': config.allow_supplementary_file,
            'require_supplementary_file': config.require_supplementary_file,
            'supplementary_file_label': config.supplementary_file_label,
            'supplementary_file_help_text': config.supplementary_file_help_text,
        })

        return kwargs

    def get_context_data(self, **kwargs):
        context = super(SubmissionCreate, self).get_context_data(**kwargs)

        config = Config.objects.get(challenge__pk=self.request.project_pk)

        date_from = timezone.now() - timedelta(days=1)
        submissions = Submission.objects.filter(
            challenge__pk=self.request.project_pk,
            creator=self.request.user,
            created__gte=date_from,
        ).order_by('created')

        remaining_submissions = config.daily_submission_limit - len(
            submissions)

        if remaining_submissions <= 0:
            next_sub_at = submissions[0].created + timedelta(days=1)
        else:
            next_sub_at = timezone.now()

        pending_jobs = Job.objects.filter(
            challenge__pk=self.request.project_pk,
            submission__creator=self.request.user,
            status=Job.PENDING,
        ).count()

        context.update({
            'remaining_submissions': remaining_submissions,
            'next_submission_at': next_sub_at,
            'pending_jobs': pending_jobs,
        })

        return context

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.challenge = ComicSite.objects.get(
            pk=self.request.project_pk)

        uploaded_file = form.cleaned_data['chunked_upload'][0]
        with uploaded_file.open() as f:
            form.instance.file.save(uploaded_file.name, File(f))

        return super(SubmissionCreate, self).form_valid(form)

    def get_success_url(self):
        return reverse(
            'evaluation:job-list',
            kwargs={
                'challenge_short_name': self.object.challenge.short_name
            }
        )


class SubmissionList(UserIsChallengeParticipantOrAdminMixin, ListView):
    model = Submission

    def get_queryset(self):
        """ Admins see everything, participants just their submissions """
        queryset = super(SubmissionList, self).get_queryset()

        challenge = ComicSite.objects.get(pk=self.request.project_pk)

        if challenge.is_admin(self.request.user):
            return queryset.filter(challenge__pk=self.request.project_pk)
        else:
            return queryset.filter(Q(challenge__pk=self.request.project_pk),
                                   Q(creator__pk=self.request.user.pk))


class SubmissionDetail(UserIsChallengeAdminMixin, DetailView):
    # TODO - if participant: list only their submissions
    model = Submission


class JobCreate(UserIsChallengeAdminMixin, CreateView):
    model = Job
    fields = '__all__'


class JobList(UserIsChallengeParticipantOrAdminMixin, ListView):
    model = Job

    def get_queryset(self):
        """ Admins see everything, participants just their jobs """
        queryset = super(JobList, self).get_queryset()
        queryset = queryset.select_related('result')

        challenge = ComicSite.objects.get(pk=self.request.project_pk)

        if challenge.is_admin(self.request.user):
            return queryset.filter(challenge__pk=self.request.project_pk)
        else:
            return queryset.filter(
                Q(challenge__pk=self.request.project_pk),
                Q(submission__creator__pk=self.request.user.pk)
            )


class JobDetail(UserIsChallengeAdminMixin, DetailView):
    # TODO - if participant: list only their jobs
    model = Job


class ResultList(ListView):
    model = Result

    def get_queryset(self):
        queryset = super(ResultList, self).get_queryset()
        queryset = queryset.select_related(
            'job__submission__creator__user_profile')
        return queryset.filter(Q(challenge__pk=self.request.project_pk),
                               Q(public=True))


class ResultDetail(DetailView):
    model = Result


class ResultUpdate(UserIsChallengeAdminMixin, SuccessMessageMixin, UpdateView):
    model = Result
    fields = ('public',)
    success_message = ('Result successfully updated.')
