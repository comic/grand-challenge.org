from datetime import datetime, timedelta
from typing import Dict

from django.contrib.messages.views import SuccessMessageMixin
from django.core.files import File
from django.db.models import Q
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from grandchallenge.core.permissions.mixins import (
    UserIsChallengeAdminMixin,
    UserIsChallengeParticipantOrAdminMixin,
)
from grandchallenge.evaluation.forms import (
    ConfigForm,
    LegacySubmissionForm,
    MethodForm,
    SubmissionForm,
)
from grandchallenge.evaluation.models import (
    Config,
    Job,
    Method,
    Result,
    Submission,
)
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile
from grandchallenge.subdomains.utils import reverse


class ConfigUpdate(UserIsChallengeAdminMixin, SuccessMessageMixin, UpdateView):
    form_class = ConfigForm
    success_message = "Configuration successfully updated"

    def get_object(self, queryset=None):
        challenge = self.request.challenge
        return challenge.evaluation_config


class MethodCreate(UserIsChallengeAdminMixin, CreateView):
    model = Method
    form_class = MethodForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.challenge = self.request.challenge

        uploaded_file: StagedAjaxFile = form.cleaned_data["chunked_upload"][0]
        form.instance.staged_image_uuid = uploaded_file.uuid

        return super().form_valid(form)


class MethodList(UserIsChallengeAdminMixin, ListView):
    model = Method

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(challenge=self.request.challenge)


class MethodDetail(UserIsChallengeAdminMixin, DetailView):
    model = Method


class SubmissionCreateBase(SuccessMessageMixin, CreateView):
    """
    Base class for the submission creation forms.

    It has no permissions, do not use it directly! See the subclasses.
    """

    model = Submission
    success_message = (
        "Your submission was successful. "
        "Your result will appear on the leaderboard when it is ready."
    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        config = Config.objects.get(
            challenge=self.request.challenge
        )  # type: Config

        kwargs.update(
            {
                "user": self.request.user,
                "display_comment_field": config.allow_submission_comments,
                "supplementary_file_choice": config.supplementary_file_choice,
                "supplementary_file_label": config.supplementary_file_label,
                "supplementary_file_help_text": config.supplementary_file_help_text,
                "publication_url_choice": config.publication_url_choice,
            }
        )

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        config = Config.objects.get(challenge=self.request.challenge)

        context.update(
            self.get_next_submission(max_subs=config.daily_submission_limit)
        )

        pending_jobs = Job.objects.filter(
            submission__challenge=self.request.challenge,
            submission__creator=self.request.user,
            status__in=(Job.PENDING, Job.STARTED),
        ).count()

        context.update({"pending_jobs": pending_jobs})

        return context

    def get_next_submission(
        self, *, max_subs: int, period: timedelta = None, now: datetime = None
    ) -> Dict:
        """
        Determines the number of submissions left for the user in a given time
        period, and when they can next submit.

        :return: A dictionary containing remaining_submissions (int) and
        next_submission_at (datetime)
        """
        if now is None:
            now = timezone.now()

        if period is None:
            period = timedelta(days=1)

        subs = (
            Submission.objects.filter(
                challenge=self.request.challenge,
                creator=self.request.user,
                created__gte=now - period,
            )
            .exclude(job__status=Job.FAILURE)
            .order_by("-created")
            .distinct()
        )

        try:
            next_sub_at = subs[max_subs - 1].created + period
        except (IndexError, AssertionError):
            next_sub_at = now

        return {
            "remaining_submissions": max_subs - len(subs),
            "next_submission_at": next_sub_at,
        }

    def form_valid(self, form):

        if form.instance.creator is None:
            form.instance.creator = self.request.user

        form.instance.challenge = self.request.challenge

        uploaded_file = form.cleaned_data["chunked_upload"][0]

        with uploaded_file.open() as f:
            form.instance.file.save(uploaded_file.name, File(f))

        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "evaluation:job-list",
            kwargs={"challenge_short_name": self.object.challenge.short_name},
        )


class SubmissionCreate(
    UserIsChallengeParticipantOrAdminMixin, SubmissionCreateBase
):
    form_class = SubmissionForm


class LegacySubmissionCreate(UserIsChallengeAdminMixin, SubmissionCreateBase):
    form_class = LegacySubmissionForm


class SubmissionList(UserIsChallengeParticipantOrAdminMixin, ListView):
    model = Submission

    def get_queryset(self):
        """Admins see everything, participants just their submissions."""
        queryset = super().get_queryset()
        challenge = self.request.challenge
        if challenge.is_admin(self.request.user):
            return queryset.filter(challenge=self.request.challenge)

        else:
            return queryset.filter(
                Q(challenge=self.request.challenge),
                Q(creator__pk=self.request.user.pk),
            )


class SubmissionDetail(UserIsChallengeAdminMixin, DetailView):
    # TODO - if participant: list only their submissions
    model = Submission


class JobCreate(UserIsChallengeAdminMixin, CreateView):
    model = Job
    fields = "__all__"


class JobList(UserIsChallengeParticipantOrAdminMixin, ListView):
    model = Job

    def get_queryset(self):
        """Admins see everything, participants just their jobs."""
        challenge = self.request.challenge

        queryset = super().get_queryset()
        queryset = queryset.select_related(
            "result", "submission__creator__user_profile"
        ).filter(submission__challenge=challenge)

        if challenge.is_admin(self.request.user):
            return queryset
        else:
            return queryset.filter(
                Q(submission__creator__pk=self.request.user.pk)
            )


class JobDetail(UserIsChallengeAdminMixin, DetailView):
    # TODO - if participant: list only their jobs
    model = Job


class ResultList(ListView):
    model = Result

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context.update(
            {
                "evaluation_config": Config.objects.get(
                    challenge=self.request.challenge
                )
            }
        )

        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.select_related(
            "job__submission__creator__user_profile"
        )
        return queryset.filter(
            Q(job__submission__challenge=self.request.challenge),
            Q(published=True),
            ~Q(rank=0),  # Exclude results without a rank
        )


class ResultDetail(DetailView):
    model = Result


class ResultUpdate(UserIsChallengeAdminMixin, SuccessMessageMixin, UpdateView):
    model = Result
    fields = ("published",)
    success_message = "Result successfully updated."
