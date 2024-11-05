from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.timezone import now
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    RedirectView,
    UpdateView,
)
from guardian.mixins import LoginRequiredMixin

from grandchallenge.algorithms.forms import AlgorithmForPhaseForm
from grandchallenge.algorithms.models import Algorithm, Job
from grandchallenge.archives.models import Archive
from grandchallenge.challenges.views import ActiveChallengeRequiredMixin
from grandchallenge.components.models import ImportStatusChoices
from grandchallenge.core.fixtures import create_uploaded_image
from grandchallenge.core.forms import UserFormKwargsMixin
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    PermissionListMixin,
    filter_by_permission,
)
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.direct_messages.forms import ConversationForm
from grandchallenge.evaluation.forms import (
    CombinedLeaderboardForm,
    ConfigureAlgorithmPhasesForm,
    EvaluationForm,
    EvaluationGroundTruthForm,
    EvaluationGroundTruthUpdateForm,
    EvaluationGroundTruthVersionManagementForm,
    MethodForm,
    MethodUpdateForm,
    PhaseCreateForm,
    PhaseUpdateForm,
    SubmissionForm,
)
from grandchallenge.evaluation.models import (
    CombinedLeaderboard,
    Evaluation,
    EvaluationGroundTruth,
    Method,
    Phase,
    Submission,
)
from grandchallenge.evaluation.tasks import create_evaluation
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.subdomains.utils import reverse, reverse_lazy
from grandchallenge.teams.models import Team
from grandchallenge.verifications.views import VerificationRequiredMixin
from grandchallenge.workstations.models import Workstation


class CachedPhaseMixin:
    @cached_property
    def phase(self):
        return get_object_or_404(
            Phase, slug=self.kwargs["slug"], challenge=self.request.challenge
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context.update({"phase": self.phase})
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"phase": self.phase})
        return kwargs


class UserCanSubmitAlgorithmToPhaseMixin(VerificationRequiredMixin):
    """
    Mixin that checks if a user is either an admin of a challenge
    or a participant of the challenge and that the phase is configured for
    algorithm submission and that the challenge has a logo.
    If the user is a participant, it also checks that the phase
    is open for submissions.
    """

    def test_func(self):
        response = super().test_func()
        if response:
            if not (
                self.phase.challenge.is_admin(self.request.user)
                or self.phase.challenge.is_participant(self.request.user)
            ):
                error_message = (
                    "You need to be either an admin or a participant of "
                    "the challenge in order to create an algorithm for this phase."
                )
                messages.error(
                    self.request,
                    error_message,
                )
                return False
            elif (
                self.phase.challenge.is_participant(self.request.user)
                and not self.phase.challenge.is_admin(self.request.user)
                and not self.phase.open_for_submissions
            ):
                error_message = "The phase is currently not open for submissions. Please come back later."
                messages.error(
                    self.request,
                    error_message,
                )
                return False
            elif (
                self.phase.challenge.is_admin(self.request.user)
                and not self.phase.challenge.logo
            ):
                error_message = (
                    "You need to first upload a logo for your challenge "
                    "before you can create algorithms for its phases."
                )
                messages.error(
                    self.request,
                    error_message,
                )
                return False
            elif (
                not self.phase.submission_kind
                == SubmissionKindChoices.ALGORITHM
                or not self.phase.algorithm_inputs
                or not self.phase.algorithm_outputs
                or not self.phase.archive
            ):
                error_message = (
                    "This phase is not configured for algorithm submission. "
                )
                if self.phase.challenge.is_admin(self.request.user):
                    error_message += "You need to link an archive containing the secret test data to this phase and define the inputs and outputs that algorithms need to read/write. Please get in touch with support@grand-challenge.org to configure these settings."
                else:
                    error_message += "Please come back later."

                messages.error(
                    self.request,
                    error_message,
                )
                return False

            return True
        else:
            return False


class PhaseCreate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    ActiveChallengeRequiredMixin,
    SuccessMessageMixin,
    CreateView,
):
    model = Phase
    form_class = PhaseCreateForm
    success_message = "Phase successfully created"
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"challenge": self.request.challenge})
        return kwargs

    def form_valid(self, form):
        form.instance.challenge = self.request.challenge
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "evaluation:phase-update",
            kwargs={
                "challenge_short_name": self.request.challenge.short_name,
                "slug": self.object.slug,
            },
        )


class PhaseUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    UpdateView,
):
    form_class = PhaseUpdateForm
    success_message = "Configuration successfully updated"
    permission_required = "change_phase"
    raise_exception = True
    login_url = reverse_lazy("account_login")
    queryset = Phase.objects.prefetch_related("optional_hanging_protocols")

    def get_object(self, queryset=None):
        return Phase.objects.get(
            challenge=self.request.challenge, slug=self.kwargs["slug"]
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {"challenge": self.request.challenge, "user": self.request.user}
        )
        return kwargs

    def get_success_url(self):
        return reverse(
            "evaluation:phase-update",
            kwargs={
                "challenge_short_name": self.request.challenge.short_name,
                "slug": self.kwargs["slug"],
            },
        )


class MethodCreate(
    LoginRequiredMixin,
    VerificationRequiredMixin,
    UserFormKwargsMixin,
    ObjectPermissionRequiredMixin,
    ActiveChallengeRequiredMixin,
    CachedPhaseMixin,
    CreateView,
):
    model = Method
    form_class = MethodForm
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge


class MethodList(
    LoginRequiredMixin, PermissionListMixin, CachedPhaseMixin, ListView
):
    model = Method
    permission_required = "view_method"
    login_url = reverse_lazy("account_login")
    ordering = ("-is_desired_version", "-created")

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(
            phase__challenge=self.request.challenge, phase=self.phase
        )


class MethodDetail(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    CachedPhaseMixin,
    DetailView,
):
    model = Method
    permission_required = "view_method"
    raise_exception = True
    login_url = reverse_lazy("account_login")


class MethodImportStatusDetail(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    DetailView,
):
    model = Method
    permission_required = "view_method"
    template_name = "components/import_status_detail.html"
    raise_exception = True
    login_url = reverse_lazy("account_login")


class MethodUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = Method
    form_class = MethodUpdateForm
    permission_required = "change_method"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update({"phase": self.object.phase})
        return context


class SubmissionCreate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    CreateView,
):
    model = Submission
    success_message = (
        "Your submission was successful. "
        "Your result will appear on the leaderboard when it is ready."
    )
    form_class = SubmissionForm
    permission_required = "create_phase_submission"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.phase

    @cached_property
    def phase(self):
        return Phase.objects.get(
            challenge=self.request.challenge, slug=self.kwargs["slug"]
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user, "phase": self.phase})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                **self.phase.get_next_submission(user=self.request.user),
                "has_pending_evaluations": self.phase.has_pending_evaluations(
                    user_pks=[self.request.user.pk]
                ),
                "phase": self.phase,
            }
        )
        return context

    def get_success_url(self):
        return reverse(
            "evaluation:submission-list",
            kwargs={
                "challenge_short_name": self.object.phase.challenge.short_name
            },
        )


class SubmissionList(LoginRequiredMixin, PermissionListMixin, ListView):
    model = Submission
    permission_required = "view_submission"
    login_url = reverse_lazy("account_login")

    def get_queryset(self):
        queryset = super().get_queryset()
        return (
            queryset.filter(phase__challenge=self.request.challenge)
            .select_related(
                "creator__user_profile",
                "creator__verification",
                "phase__challenge",
            )
            .prefetch_related(
                "evaluation_set", "phase__optional_hanging_protocols"
            )
        )


class SubmissionDetail(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    CachedPhaseMixin,
    DetailView,
):
    model = Submission
    permission_required = "view_submission"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related("phase__optional_hanging_protocols")
        )


class TeamContextMixin:
    @cached_property
    def user_teams(self):
        if self.request.challenge.use_teams:
            user_teams = {
                teammember.user.username: (team.name, team.get_absolute_url())
                for team in Team.objects.filter(
                    challenge=self.request.challenge
                )
                .select_related("challenge")
                .prefetch_related("teammember_set__user")
                for teammember in team.teammember_set.all()
            }
        else:
            user_teams = {}

        return user_teams

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"user_teams": self.user_teams})
        return context


class EvaluationCreate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    form_class = EvaluationForm
    permission_required = "change_challenge"
    login_url = reverse_lazy("account_login")
    raise_exception = True
    success_message = "A job to create the new evaluation is running, please check back later"
    template_name = "evaluation/evaluation_form.html"

    def get_permission_object(self):
        return self.request.challenge

    @cached_property
    def submission(self):
        return get_object_or_404(
            Submission,
            pk=self.kwargs["pk"],
            phase__slug=self.kwargs["slug"],
            phase__challenge=self.request.challenge,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "user": self.request.user,
                "submission": self.submission,
            }
        )
        return kwargs

    def get_success_url(self):
        return self.submission.get_absolute_url()

    def form_valid(self, form):
        redirect = super().form_valid(form)
        create_evaluation.apply_async(
            kwargs={"submission_pk": str(form.cleaned_data["submission"].pk)}
        )
        return redirect


class EvaluationList(
    LoginRequiredMixin,
    PermissionListMixin,
    TeamContextMixin,
    CachedPhaseMixin,
    ListView,
):
    model = Evaluation
    permission_required = "view_evaluation"
    login_url = reverse_lazy("account_login")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = (
            queryset.filter(
                submission__phase__challenge=self.request.challenge,
                submission__phase=self.phase,
            )
            .select_related(
                "submission__creator__user_profile",
                "submission__creator__verification",
                "submission__phase__challenge",
                "submission__algorithm_image__algorithm",
            )
            .prefetch_related("submission__phase__optional_hanging_protocols")
        )

        if self.request.challenge.is_admin(self.request.user):
            return queryset
        else:
            return queryset.filter(
                Q(submission__creator__pk=self.request.user.pk)
            )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data()
        context.update({"base_template": "base.html"})
        return context


class EvaluationAdminList(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    TeamContextMixin,
    CachedPhaseMixin,
    ListView,
):
    model = Evaluation
    permission_required = "change_challenge"
    login_url = reverse_lazy("account_login")
    raise_exception = True

    def get_permission_object(self):
        return self.request.challenge

    def get_queryset(self):
        queryset = super().get_queryset()
        return (
            queryset.filter(
                submission__phase__challenge=self.request.challenge,
                submission__phase=self.phase,
            )
            .select_related(
                "submission__creator__user_profile",
                "submission__creator__verification",
                "submission__phase__challenge",
                "submission__algorithm_image__algorithm",
            )
            .prefetch_related("submission__phase__optional_hanging_protocols")
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data()
        context.update({"base_template": "pages/challenge_settings_base.html"})
        return context


class EvaluationDetail(ObjectPermissionRequiredMixin, DetailView):
    model = Evaluation
    permission_required = "view_evaluation"
    raise_exception = True

    def get_conversation_form(self):
        if self.object.submission.creator:
            conversation_form = ConversationForm(
                participants=get_user_model().objects.filter(
                    pk__in={
                        self.request.user.pk,
                        self.object.submission.creator.pk,
                    }
                )
            )
            conversation_form.helper.form_action = reverse(
                "direct_messages:conversation-create",
                kwargs={"username": self.object.submission.creator.username},
            )
        else:
            conversation_form = None

        return conversation_form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            metrics = self.object.outputs.get(
                interface__slug="metrics-json-file"
            ).value
        except ObjectDoesNotExist:
            metrics = None

        try:
            predictions = self.object.inputs.get(
                interface__slug="predictions-json-file"
            ).value
        except ObjectDoesNotExist:
            predictions = None

        incomplete_jobs = filter_by_permission(
            queryset=Job.objects.exclude(status=Job.SUCCESS)
            .filter(
                algorithm_image=self.object.submission.algorithm_image,
                inputs__archive_items__archive=self.object.submission.phase.archive,
            )
            .distinct()
            .order_by("status"),
            user=self.request.user,
            codename="view_job",
        )

        context.update(
            {
                "metrics": metrics,
                "predictions": predictions,
                "incomplete_jobs": incomplete_jobs,
                "conversation_form": self.get_conversation_form(),
            }
        )

        return context


class EvaluationStatusBadgeDetail(ObjectPermissionRequiredMixin, DetailView):
    permission_required = "view_evaluation"
    template_name_suffix = "_status_badge_detail"
    model = Evaluation
    raise_exception = True


class LeaderboardRedirect(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        # Redirect old leaderboard urls to the first leaderboard for this
        # challenge
        first_phase = self.request.challenge.phase_set.first()
        if first_phase:
            return reverse(
                "evaluation:leaderboard",
                kwargs={
                    "challenge_short_name": first_phase.challenge.short_name,
                    "slug": first_phase.slug,
                },
            )
        else:
            raise Http404("Leaderboard not found")


class LeaderboardDetail(
    UserPassesTestMixin, TeamContextMixin, PaginatedTableListView
):
    model = Evaluation
    template_name = "evaluation/leaderboard_detail.html"
    row_template = "evaluation/leaderboard_row.html"
    search_fields = ["pk", "submission__creator__username"]

    def test_func(self):
        if self.phase.public:
            return True
        else:
            return self.phase.challenge.is_admin(user=self.request.user)

    @cached_property
    def phase(self):
        return get_object_or_404(
            klass=Phase,
            challenge=self.request.challenge,
            slug=self.kwargs["slug"],
        )

    @property
    def columns(self):
        columns = []

        columns.extend(
            [
                Column(
                    title="Current #" if "date" in self.request.GET else "#",
                    sort_field="rank",
                ),
                Column(
                    title=(
                        "User (Team)"
                        if self.request.challenge.use_teams
                        else "User"
                    ),
                    sort_field="submission__creator__username",
                ),
            ]
        )

        if self.phase.submission_kind == SubmissionKindChoices.ALGORITHM:
            columns.append(
                Column(
                    title="Algorithm",
                    sort_field="submission__algorithm_image__algorithm__title",
                )
            )

        columns.append(
            Column(title="Created", sort_field="submission__created")
        )

        if self.phase.scoring_method_choice == self.phase.MEAN:
            columns.append(Column(title="Mean Position", sort_field="rank"))
        elif self.phase.scoring_method_choice == self.phase.MEDIAN:
            columns.append(Column(title="Median Position", sort_field="rank"))

        if self.phase.scoring_method_choice == self.phase.ABSOLUTE:
            columns.append(
                Column(title=self.phase.score_title, sort_field="rank")
            )
        else:
            columns.append(
                Column(
                    title=f"{self.phase.score_title} (Position)",
                    sort_field="rank",
                    classes=("toggleable",),
                )
            )

        for c in self.phase.extra_results_columns:
            columns.append(
                Column(
                    title=(
                        c["title"]
                        if self.phase.scoring_method_choice
                        == self.phase.ABSOLUTE
                        or c.get("exclude_from_ranking", False)
                        else f"{c['title']} (Position)"
                    ),
                    sort_field="rank",
                    classes=("toggleable",),
                )
            )

        if self.phase.display_submission_comments:
            columns.append(
                Column(title="Comment", sort_field="submission__comment")
            )

        if self.phase.show_supplementary_url:
            columns.append(
                Column(
                    title=self.phase.supplementary_url_label,
                    sort_field="submission__supplementary_url",
                )
            )

        if self.phase.show_supplementary_file_link:
            columns.append(
                Column(
                    title=self.phase.supplementary_file_label,
                    sort_field="submission__supplementary_file",
                    classes=("nonSortable",),
                )
            )

        return columns

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "phase": self.phase,
                "now": now().isoformat(),
                "limit": 1000,
                "user_teams": self.user_teams,
                "allow_metrics_toggling": len(self.phase.extra_results_columns)
                > 0
                or self.phase.scoring_method_choice != self.phase.ABSOLUTE,
                "display_leaderboard_date_button": self.phase.result_display_choice
                == self.phase.ALL,
            }
        )
        return context

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        queryset = self.filter_by_date(queryset=queryset)
        queryset = (
            queryset.filter(
                submission__phase=self.phase,
                published=True,
                status=Evaluation.SUCCESS,
                rank__gt=0,
            )
            .select_related(
                "submission__creator__user_profile",
                "submission__creator__verification",
                "submission__phase__challenge",
                "submission__algorithm_image__algorithm",
            )
            .prefetch_related(
                "outputs__interface",
            )
        )
        return filter_by_permission(
            queryset=queryset,
            user=self.request.user,
            codename="view_evaluation",
            accept_user_perms=False,
        )

    def filter_by_date(self, queryset):
        if "date" in self.request.GET:
            year, month, day = self.request.GET["date"].split("-")
            before = datetime(
                year=int(year), month=int(month), day=int(day)
            ) + relativedelta(days=1)
            return queryset.filter(submission__created__lt=before)
        else:
            return queryset


class EvaluationUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = Evaluation
    fields = ("published",)
    success_message = "Result successfully updated."
    permission_required = "change_evaluation"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_success_url(self):
        next = self.request.GET.get("next")
        admin_list_url = reverse(
            "evaluation:evaluation-admin-list",
            kwargs={
                "slug": self.object.submission.phase.slug,
                "challenge_short_name": self.object.submission.phase.challenge.short_name,
            },
        )

        if next == admin_list_url:
            return next
        else:
            return super().get_success_url()


class PhaseAlgorithmCreate(
    LoginRequiredMixin,
    UserCanSubmitAlgorithmToPhaseMixin,
    CreateView,
):
    model = Algorithm
    form_class = AlgorithmForPhaseForm

    def form_valid(self, form):
        response = super().form_valid(form=form)
        self.object.add_editor(self.request.user)
        return response

    @cached_property
    def phase(self):
        return Phase.objects.get(
            slug=self.kwargs["slug"], challenge=self.request.challenge
        )

    def get_success_url(self):
        return (
            reverse("algorithms:detail", kwargs={"slug": self.object.slug})
            + "#containers"
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "workstation_config": self.phase.workstation_config,
                "hanging_protocol": self.phase.hanging_protocol,
                "optional_hanging_protocols": self.phase.optional_hanging_protocols.all(),
                "view_content": self.phase.view_content,
                "display_editors": True,
                "contact_email": self.request.user.email,
                "workstation": self.phase.workstation,
                "inputs": self.phase.algorithm_inputs.all(),
                "outputs": self.phase.algorithm_outputs.all(),
                "modalities": self.phase.challenge.modalities.all(),
                "structures": self.phase.challenge.structures.all(),
                "logo": self.phase.challenge.logo,
                "user": self.request.user,
                "phase": self.phase,
            }
        )

        return kwargs

    def hide_form(self, form):
        show_form = self.request.GET.get("show_form", None)
        alg_count = form.user_algorithm_count
        if alg_count < settings.ALGORITHMS_MAX_NUMBER_PER_USER_PER_PHASE and (
            show_form or self.request.method == "POST" or alg_count == 0
        ):
            return False
        else:
            return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        form = context["form"]
        context.update(
            {
                "user_algorithm_count": form.user_algorithm_count,
                "user_algorithms": form.user_algorithms_for_phase,
                "max_num_algorithms": settings.ALGORITHMS_MAX_NUMBER_PER_USER_PER_PHASE,
                "hide_form": self.hide_form(form=form),
            }
        )
        return context


class CombinedLeaderboardCreate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    CreateView,
):
    model = CombinedLeaderboard
    form_class = CombinedLeaderboardForm
    success_message = "A job has been scheduled to update the combined leaderboard ranks, please check back later."
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"challenge": self.request.challenge})
        return kwargs

    def form_valid(self, form):
        form.instance.challenge = self.request.challenge
        return super().form_valid(form)


class CombinedLeaderboardDetail(DetailView):
    model = CombinedLeaderboard

    def get_object(self, queryset=None):
        return get_object_or_404(
            CombinedLeaderboard,
            challenge=self.request.challenge,
            slug=self.kwargs["slug"],
        )


class CombinedLeaderboardUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = CombinedLeaderboard
    form_class = CombinedLeaderboardForm
    success_message = "A job has been scheduled to update the combined leaderboard ranks, please check back later."
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_object(self, queryset=None):
        return get_object_or_404(
            CombinedLeaderboard,
            challenge=self.request.challenge,
            slug=self.kwargs["slug"],
        )

    def get_permission_object(self):
        return self.get_object().challenge

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"challenge": self.object.challenge})
        return kwargs


class CombinedLeaderboardDelete(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    DeleteView,
):
    model = CombinedLeaderboard
    success_message = "The combined leaderboard was deleted."
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_object(self, queryset=None):
        return get_object_or_404(
            CombinedLeaderboard,
            challenge=self.request.challenge,
            slug=self.kwargs["slug"],
        )

    def get_success_url(self):
        return reverse(
            "challenge-update",
            kwargs={
                "challenge_short_name": self.request.challenge.short_name,
            },
        )

    def get_permission_object(self):
        return self.get_object().challenge


class ConfigureAlgorithmPhasesView(PermissionRequiredMixin, FormView):
    form_class = ConfigureAlgorithmPhasesForm
    permission_required = "evaluation.configure_algorithm_phase"
    template_name = "evaluation/configure_algorithm_phases_form.html"
    raise_exception = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"challenge": self.request.challenge})
        return kwargs

    def form_valid(self, form):
        for phase in form.cleaned_data["phases"]:
            self.turn_phase_into_algorithm_phase(
                phase=phase,
                inputs=form.cleaned_data["algorithm_inputs"],
                outputs=form.cleaned_data["algorithm_outputs"],
                algorithm_time_limit=form.cleaned_data["algorithm_time_limit"],
            )
        messages.success(self.request, "Phases were successfully updated")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "challenges:requests-list",
        )

    def turn_phase_into_algorithm_phase(
        self, *, phase, inputs, outputs, algorithm_time_limit
    ):
        archive = Archive.objects.create(
            title=format_html(
                "{challenge_name} {phase_title} dataset",
                challenge_name=phase.challenge.short_name,
                phase_title=phase.title,
            ),
            workstation=Workstation.objects.get(
                slug=settings.DEFAULT_WORKSTATION_SLUG
            ),
            logo=(
                phase.challenge.logo
                if phase.challenge.logo
                else create_uploaded_image()
            ),
        )
        archive.full_clean()
        archive.save()

        for user in phase.challenge.admins_group.user_set.all():
            archive.add_editor(user)

        phase.algorithm_time_limit = algorithm_time_limit
        phase.archive = archive
        phase.submission_kind = phase.SubmissionKindChoices.ALGORITHM
        phase.creator_must_be_verified = True
        phase.save()
        phase.algorithm_outputs.add(*outputs)
        phase.algorithm_inputs.add(*inputs)


class EvaluationGroundTruthCreate(
    LoginRequiredMixin,
    VerificationRequiredMixin,
    UserFormKwargsMixin,
    ObjectPermissionRequiredMixin,
    ActiveChallengeRequiredMixin,
    CachedPhaseMixin,
    SuccessMessageMixin,
    CreateView,
):
    model = EvaluationGroundTruth
    form_class = EvaluationGroundTruthForm
    permission_required = "evaluation.change_phase"
    raise_exception = True
    success_message = "Ground truth upload in progress."

    def get_permission_object(self):
        return self.phase


class EvaluationGroundTruthDetail(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    DetailView,
):
    model = EvaluationGroundTruth
    permission_required = "evaluation.view_evaluationgroundtruth"
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form_kwargs = {
            "initial": {"ground_truth": self.object.pk},
            "user": self.request.user,
            "phase": self.object.phase,
            "hide_ground_truth_input": True,
        }

        context.update(
            {
                "import_choices": ImportStatusChoices,
                "gt_activate_form": EvaluationGroundTruthVersionManagementForm(
                    activate=True, **form_kwargs
                ),
                "gt_deactivate_form": EvaluationGroundTruthVersionManagementForm(
                    activate=False, **form_kwargs
                ),
            }
        )

        return context


class EvaluationGroundTruthImportStatusDetail(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    DetailView,
):
    model = EvaluationGroundTruth
    permission_required = "evaluation.view_evaluationgroundtruth"
    template_name = "components/import_status_detail.html"
    raise_exception = True


class EvaluationGroundTruthList(
    LoginRequiredMixin, PermissionListMixin, CachedPhaseMixin, ListView
):
    model = EvaluationGroundTruth
    permission_required = "evaluation.view_evaluationgroundtruth"
    login_url = reverse_lazy("account_login")
    ordering = ("-is_desired_version", "-created")

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(phase=self.phase)


class EvaluationGroundTruthUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = EvaluationGroundTruth
    form_class = EvaluationGroundTruthUpdateForm
    permission_required = "change_evaluationgroundtruth"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update({"phase": self.object.phase})
        return context


class EvaluationGroundTruthVersionManagement(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    CachedPhaseMixin,
    SuccessMessageMixin,
    FormView,
):
    permission_required = "evaluation.change_phase"
    raise_exception = True
    form_class = EvaluationGroundTruthVersionManagementForm
    template_name = "evaluation/ground_truth_version_management.html"
    success_message = "Ground truth successfully activated."
    activate = None

    def get_permission_object(self):
        return self.phase

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "user": self.request.user,
                "activate": self.activate,
            }
        )
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form=form)
        ground_truth = form.cleaned_data["ground_truth"]
        if self.activate:
            ground_truth.mark_desired_version()
        else:
            ground_truth.is_desired_version = False
            ground_truth.save()
        return response

    def get_success_url(self):
        return reverse(
            "evaluation:ground-truth-list",
            kwargs={
                "challenge_short_name": self.phase.challenge.short_name,
                "slug": self.phase.slug,
            },
        )


class PhaseArchiveInfo(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = Phase
    permission_required = "evaluation.change_phase"
    raise_exception = True
    template_name = "evaluation/phase_archive_info.html"

    def get_object(self, queryset=None):
        return get_object_or_404(
            Phase,
            challenge=self.request.challenge,
            slug=self.kwargs["slug"],
        )
