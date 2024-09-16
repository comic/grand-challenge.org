import logging
from datetime import timedelta
from statistics import mean, median

from actstream.actions import follow, is_following
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.mail import mail_managers
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count, Q
from django.db.transaction import on_commit
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.text import get_valid_filename
from django.utils.timezone import localtime
from django_extensions.db.fields import AutoSlugField
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.algorithms.models import AlgorithmImage, AlgorithmModel
from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.challenges.models import Challenge
from grandchallenge.components.models import (
    ComponentImage,
    ComponentInterface,
    ComponentJob,
    ImportStatusChoices,
    Tarball,
)
from grandchallenge.core.models import (
    FieldChangeMixin,
    TitleSlugDescriptionModel,
    UUIDModel,
)
from grandchallenge.core.storage import (
    private_s3_storage,
    protected_s3_storage,
    public_s3_storage,
)
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.core.validators import (
    ExtensionValidator,
    JSONValidator,
    MimeTypeValidator,
)
from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.evaluation.tasks import (
    assign_evaluation_permissions,
    assign_submission_permissions,
    calculate_ranks,
    create_evaluation,
    update_combined_leaderboard,
)
from grandchallenge.evaluation.templatetags.evaluation_extras import (
    get_jsonpath,
)
from grandchallenge.evaluation.utils import (
    Metric,
    StatusChoices,
    SubmissionKindChoices,
)
from grandchallenge.hanging_protocols.models import HangingProtocolMixin
from grandchallenge.notifications.models import Notification, NotificationType
from grandchallenge.profiles.models import EmailSubscriptionTypes
from grandchallenge.profiles.tasks import deactivate_user
from grandchallenge.subdomains.utils import reverse
from grandchallenge.uploads.models import UserUpload
from grandchallenge.verifications.models import VerificationUserSet

logger = logging.getLogger(__name__)

EXTRA_RESULT_COLUMNS_SCHEMA = {
    "definitions": {},
    "$schema": "http://json-schema.org/draft-06/schema#",
    "type": "array",
    "title": "The Extra Results Columns Schema",
    "items": {
        "$id": "#/items",
        "type": "object",
        "title": "The Items Schema",
        "required": ["title", "path", "order"],
        "additionalProperties": False,
        "properties": {
            "title": {
                "$id": "#/items/properties/title",
                "type": "string",
                "title": "The Title Schema",
                "default": "",
                "examples": ["Mean Dice"],
                "pattern": "^(.*)$",
            },
            "path": {
                "$id": "#/items/properties/path",
                "type": "string",
                "title": "The Path Schema",
                "default": "",
                "examples": ["aggregates.dice.mean"],
                "pattern": "^(.*)$",
            },
            "error_path": {
                "$id": "#/items/properties/error_path",
                "type": "string",
                "title": "The Error Path Schema",
                "default": "",
                "examples": ["aggregates.dice.std"],
                "pattern": "^(.*)$",
            },
            "order": {
                "$id": "#/items/properties/order",
                "type": "string",
                "enum": ["asc", "desc"],
                "title": "The Order Schema",
                "default": "",
                "examples": ["asc"],
                "pattern": "^(asc|desc)$",
            },
            "exclude_from_ranking": {
                "$id": "#/items/properties/exclude_from_ranking",
                "type": "boolean",
                "title": "The Exclude From Ranking Schema",
                "default": False,
            },
        },
    },
}


class PhaseManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                # This should be a select_related, but I cannot find a way
                # to use a custom model manager with select_related
                # Maybe this is solved with GeneratedField (Django 5)?
                models.Prefetch(
                    "challenge",
                    queryset=Challenge.objects.with_available_compute(),
                )
            )
        )


SUBMISSION_WINDOW_PARENT_VALIDATION_TEXT = (
    "The parent phase needs to open submissions before the current "
    "phase since submissions to this phase will only be possible "
    "after successful submission to the parent phase."
)


class Phase(FieldChangeMixin, HangingProtocolMixin, UUIDModel):
    # This must match the syntax used in jquery datatables
    # https://datatables.net/reference/option/order
    ASCENDING = "asc"
    DESCENDING = "desc"
    EVALUATION_SCORE_SORT_CHOICES = (
        (ASCENDING, "Ascending"),
        (DESCENDING, "Descending"),
    )

    OFF = "off"
    OPTIONAL = "opt"
    REQUIRED = "req"
    SUPPLEMENTARY_URL_CHOICES = SUPPLEMENTARY_FILE_CHOICES = (
        (OFF, "Off"),
        (OPTIONAL, "Optional"),
        (REQUIRED, "Required"),
    )

    ALL = "all"
    MOST_RECENT = "rec"
    BEST = "bst"
    RESULT_DISPLAY_CHOICES = (
        (ALL, "Display all results"),
        (MOST_RECENT, "Only display each users most recent result"),
        (BEST, "Only display each users best result"),
    )

    ABSOLUTE = "abs"
    MEAN = "avg"
    MEDIAN = "med"
    SCORING_CHOICES = (
        (ABSOLUTE, "Use the absolute value of the score column"),
        (
            MEAN,
            "Use the mean of the relative ranks of the score and extra result columns",
        ),
        (
            MEDIAN,
            "Use the median of the relative ranks of the score and extra result columns",
        ),
    )

    SubmissionKindChoices = SubmissionKindChoices
    StatusChoices = StatusChoices

    challenge = models.ForeignKey(
        Challenge, on_delete=models.PROTECT, editable=False
    )
    archive = models.ForeignKey(
        Archive,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=(
            "Which archive should be used as the source dataset for this "
            "phase?"
        ),
    )
    title = models.CharField(
        max_length=64,
        help_text="The title of this phase.",
    )
    slug = AutoSlugField(populate_from="title", max_length=64)
    score_title = models.CharField(
        max_length=32,
        blank=False,
        default="Score",
        help_text=(
            "The name that will be displayed for the scores column, for "
            "instance: Score (log-loss)"
        ),
    )
    score_jsonpath = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "The jsonpath of the field in metrics.json that will be used "
            "for the overall scores on the results page. See "
            "http://goessner.net/articles/JsonPath/ for syntax. For example: "
            "dice.mean"
        ),
    )
    score_error_jsonpath = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "The jsonpath for the field in metrics.json that contains the "
            "error of the score, eg: dice.std"
        ),
    )
    score_default_sort = models.CharField(
        max_length=4,
        choices=EVALUATION_SCORE_SORT_CHOICES,
        default=DESCENDING,
        help_text=(
            "The default sorting to use for the scores on the results page."
        ),
    )
    score_decimal_places = models.PositiveSmallIntegerField(
        blank=False,
        default=4,
        help_text=("The number of decimal places to display for the score"),
    )
    extra_results_columns = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "A JSON object that contains the extra columns from metrics.json "
            "that will be displayed on the results page. An example that will display "
            "accuracy score with error would look like this: "
            "[{"
            '"path": "accuracy.mean",'
            '"order": "asc",'
            '"title": "ASSD +/- std",'
            '"error_path": "accuracy.std",'
            '"exclude_from_ranking": true'
            "}]"
        ),
        validators=[JSONValidator(schema=EXTRA_RESULT_COLUMNS_SCHEMA)],
    )
    scoring_method_choice = models.CharField(
        max_length=3,
        choices=SCORING_CHOICES,
        default=ABSOLUTE,
        help_text=("How should the rank of each result be calculated?"),
    )
    result_display_choice = models.CharField(
        max_length=3,
        choices=RESULT_DISPLAY_CHOICES,
        default=ALL,
        help_text=("Which results should be displayed on the leaderboard?"),
    )
    creator_must_be_verified = models.BooleanField(
        default=False,
        help_text=(
            "If True, only participants with verified accounts can make "
            "submissions to this phase"
        ),
    )
    submission_kind = models.PositiveSmallIntegerField(
        default=SubmissionKindChoices.CSV,
        choices=SubmissionKindChoices.choices,
        help_text=(
            "Should participants submit a .csv/.zip file of predictions, "
            "or an algorithm?"
        ),
    )
    allow_submission_comments = models.BooleanField(
        default=False,
        help_text=(
            "Allow users to submit comments as part of their submission."
        ),
    )
    display_submission_comments = models.BooleanField(
        default=False,
        help_text=(
            "If true, submission comments are shown on the results page."
        ),
    )
    supplementary_file_choice = models.CharField(
        max_length=3,
        choices=SUPPLEMENTARY_FILE_CHOICES,
        default=OFF,
        help_text=(
            "Show a supplementary file field on the submissions page so that "
            "users can upload an additional file along with their predictions "
            "file as part of their submission (eg, include a pdf description "
            "of their method). Off turns this feature off, Optional means "
            "that including the file is optional for the user, Required means "
            "that the user must upload a supplementary file."
        ),
    )
    supplementary_file_label = models.CharField(
        max_length=32,
        blank=True,
        default="Supplementary File",
        help_text=(
            "The label that will be used on the submission and results page "
            "for the supplementary file. For example: Algorithm Description."
        ),
    )
    supplementary_file_help_text = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text=(
            "The help text to include on the submissions page to describe the "
            'submissions file. Eg: "A PDF description of the method.".'
        ),
    )
    show_supplementary_file_link = models.BooleanField(
        default=False,
        help_text=(
            "Show a link to download the supplementary file on the results "
            "page."
        ),
    )
    supplementary_url_choice = models.CharField(
        max_length=3,
        choices=SUPPLEMENTARY_URL_CHOICES,
        default=OFF,
        help_text=(
            "Show a supplementary url field on the submission page so that "
            "users can submit a link to a publication that corresponds to "
            "their submission. Off turns this feature off, Optional means "
            "that including the url is optional for the user, Required means "
            "that the user must provide an url."
        ),
    )
    supplementary_url_label = models.CharField(
        max_length=32,
        blank=True,
        default="Publication",
        help_text=(
            "The label that will be used on the submission and results page "
            "for the supplementary url. For example: Publication."
        ),
    )
    supplementary_url_help_text = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text=(
            "The help text to include on the submissions page to describe the "
            'submissions url. Eg: "A link to your publication.".'
        ),
    )
    show_supplementary_url = models.BooleanField(
        default=False,
        help_text=("Show a link to the supplementary url on the results page"),
    )
    submissions_limit_per_user_per_period = models.PositiveIntegerField(
        default=0,
        help_text=(
            "The limit on the number of times that a user can make a "
            "submission over the submission limit period. "
            "Set this to 0 to close submissions for this phase."
        ),
    )
    submission_limit_period = models.PositiveSmallIntegerField(
        default=1,
        null=True,
        blank=True,
        help_text=(
            "The number of days to consider for the submission limit period. "
            "If this is set to 1, then the submission limit is applied "
            "over the previous day. If it is set to 365, then the submission "
            "limit is applied over the previous year. If the value is not "
            "set, then the limit is applied over all time."
        ),
        validators=[MinValueValidator(limit_value=1)],
    )
    submissions_open_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "If set, participants will not be able to make submissions to "
            "this phase before this time. Enter the date and time in your local "
            "timezone."
        ),
    )
    submissions_close_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "If set, participants will not be able to make submissions to "
            "this phase after this time. Enter the date and time in your local "
            "timezone."
        ),
    )
    submission_page_html = models.TextField(
        help_text=(
            "HTML to include on the submission page for this challenge."
        ),
        blank=True,
    )
    auto_publish_new_results = models.BooleanField(
        default=True,
        help_text=(
            "If true, new results are automatically made public. If false, "
            "the challenge administrator must manually publish each new "
            "result."
        ),
    )
    display_all_metrics = models.BooleanField(
        default=True,
        help_text=(
            "Should all of the metrics be displayed on the Result detail page?"
        ),
    )

    inputs = models.ManyToManyField(
        to=ComponentInterface, related_name="evaluation_inputs"
    )
    outputs = models.ManyToManyField(
        to=ComponentInterface, related_name="evaluation_outputs"
    )
    algorithm_inputs = models.ManyToManyField(
        to=ComponentInterface,
        related_name="+",
        blank=True,
        help_text="The input interfaces that the algorithms for this phase must use",
    )
    algorithm_outputs = models.ManyToManyField(
        to=ComponentInterface,
        related_name="+",
        blank=True,
        help_text="The output interfaces that the algorithms for this phase must use",
    )
    algorithm_time_limit = models.PositiveIntegerField(
        default=20 * 60,
        help_text="Time limit for inference jobs in seconds",
        validators=[
            MinValueValidator(
                limit_value=settings.COMPONENTS_MINIMUM_JOB_DURATION
            ),
            MaxValueValidator(
                limit_value=settings.COMPONENTS_MAXIMUM_JOB_DURATION
            ),
        ],
    )
    give_algorithm_editors_job_view_permissions = models.BooleanField(
        default=False,
        help_text=(
            "If set to True algorithm editors (i.e. challenge participants) "
            "will automatically be given view permissions to the algorithm "
            "jobs and their logs associated with this phase. "
            "This saves challenge administrators from having to "
            "manually share the logs for each failed submission. "
            "<b>Setting this to True will essentially make the data in "
            "the linked archive accessible to the participants. "
            "Only set this to True for debugging phases, where "
            "participants can check that their algorithms are working.</b> "
            "Algorithm editors will only be able to access their own "
            "logs and predictions, not the logs and predictions from "
            "other users. "
        ),
    )
    evaluation_time_limit = models.PositiveIntegerField(
        default=60 * 60,
        help_text="Time limit for evaluation jobs in seconds",
        validators=[
            MinValueValidator(
                limit_value=settings.COMPONENTS_MINIMUM_JOB_DURATION
            ),
            MaxValueValidator(
                limit_value=settings.COMPONENTS_MAXIMUM_JOB_DURATION
            ),
        ],
    )
    public = models.BooleanField(
        default=True,
        help_text=(
            "Uncheck this box to hide this phase's submission page and "
            "leaderboard from participants. Participants will then no longer "
            "have access to their previous submissions and evaluations from this "
            "phase if they exist, and they will no longer see the "
            "respective submit and leaderboard tabs for this phase. "
            "For you as admin these tabs remain visible. "
            "Note that hiding a phase is only possible if submissions for "
            "this phase are closed for participants."
        ),
    )
    workstation = models.ForeignKey(
        "workstations.Workstation",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    workstation_config = models.ForeignKey(
        "workstation_configs.WorkstationConfig",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    optional_hanging_protocols = models.ManyToManyField(
        "hanging_protocols.HangingProtocol",
        through="OptionalHangingProtocolPhase",
        related_name="optional_for_phase",
        blank=True,
        help_text="Optional alternative hanging protocols for this phase",
    )

    average_algorithm_job_duration = models.DurationField(
        editable=False,
        null=True,
        help_text="The average duration of successful algorithm jobs for this phase",
    )
    compute_cost_euro_millicents = models.PositiveBigIntegerField(
        # We store euro here as the costs were incurred at a time when
        # the exchange rate may have been different
        editable=False,
        default=0,
        help_text="The total compute cost for this phase in Euro Cents, including Tax",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
        help_text=(
            "Is this phase dependent on another phase? If selected, submissions "
            "to the current phase will only be possible after a successful "
            "submission has been made to the parent phase. "
            "<b>Bear in mind that if you require a successful submission to a "
            "sanity check phase in order to submit to a final test phase, "
            "it could prevent people from submitting to the test phase on deadline "
            "day if the sanity check submission takes a long time to execute. </b>"
        ),
    )

    objects = PhaseManager()

    class Meta:
        unique_together = (("challenge", "title"), ("challenge", "slug"))
        ordering = ("challenge", "submissions_open_at", "created")
        permissions = (
            ("create_phase_submission", "Create Phase Submission"),
            ("configure_algorithm_phase", "Configure Algorithm Phase"),
        )

    def __str__(self):
        return f"{self.title} Evaluation for {self.challenge.short_name}"

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.set_default_interfaces()
            self.assign_permissions()
            for admin in self.challenge.get_admins():
                if not is_following(admin, self):
                    follow(
                        user=admin,
                        obj=self,
                        actor_only=False,
                        send_action=False,
                    )

        if self.has_changed("public"):
            self.assign_permissions()
            on_commit(
                assign_evaluation_permissions.signature(
                    kwargs={"phase_pks": [self.pk]}
                ).apply_async
            )
            on_commit(
                assign_submission_permissions.signature(
                    kwargs={"phase_pk": self.pk}
                ).apply_async
            )

        if (
            self.give_algorithm_editors_job_view_permissions
            and self.has_changed("give_algorithm_editors_job_view_permissions")
        ):
            self.send_give_algorithm_editors_job_view_permissions_changed_email()

        on_commit(
            lambda: calculate_ranks.apply_async(kwargs={"phase_pk": self.pk})
        )

    def clean(self):
        super().clean()
        self._clean_algorithm_submission_settings()
        self._clean_submission_limits()
        try:
            self._clean_parent_phase()
        except ValidationError as e:
            raise ValidationError({"parent": e})

    def _clean_algorithm_submission_settings(self):
        if self.submission_kind == SubmissionKindChoices.ALGORITHM:
            if not self.creator_must_be_verified:
                raise ValidationError(
                    "For phases that take an algorithm as submission input, "
                    "the creator_must_be_verified box needs to be checked."
                )
            if self.submissions_limit_per_user_per_period > 0 and (
                not self.archive
                or not self.algorithm_inputs
                or not self.algorithm_outputs
            ):
                raise ValidationError(
                    "To change the submission limit to above 0, you need to first link an archive containing the secret "
                    "test data to this phase and define the inputs and outputs that the submitted algorithms need to "
                    "read/write. To configure these settings, please get in touch with support@grand-challenge.org."
                )
        if (
            self.give_algorithm_editors_job_view_permissions
            and not self.submission_kind
            == self.SubmissionKindChoices.ALGORITHM
        ):
            raise ValidationError(
                "Give Algorithm Editors Job View Permissions can only be enabled for Algorithm type phases"
            )

    def _clean_submission_limits(self):
        if (
            self.submissions_limit_per_user_per_period > 0
            and not self.active_image
        ):
            raise ValidationError(
                "You need to first add a valid method for this phase before you "
                "can change the submission limit to above 0."
            )

        if (
            self.submissions_open_at
            and self.submissions_close_at
            and self.submissions_close_at < self.submissions_open_at
        ):
            raise ValidationError(
                "The submissions close date needs to be after "
                "the submissions open date."
            )

        if not self.public and self.open_for_submissions:
            raise ValidationError(
                "A phase can only be hidden if it is closed for submissions. "
                "To close submissions for this phase, either set "
                "submissions_limit_per_user_per_period to 0, or set appropriate phase start / end dates."
            )

        if (
            self.submissions_open_at
            and self.parent
            and self.parent.submissions_open_at
            and self.submissions_open_at < self.parent.submissions_open_at
        ):
            raise ValidationError(SUBMISSION_WINDOW_PARENT_VALIDATION_TEXT)

    @property
    def scoring_method(self):
        if self.scoring_method_choice == self.ABSOLUTE:

            def scoring_method(x):
                return list(x)[0]

        elif self.scoring_method_choice == self.MEAN:
            scoring_method = mean
        elif self.scoring_method_choice == self.MEDIAN:
            scoring_method = median
        else:
            raise NotImplementedError

        return scoring_method

    @cached_property
    def valid_metrics(self):
        return (
            Metric(
                path=self.score_jsonpath,
                reverse=(self.score_default_sort == self.DESCENDING),
            ),
            *[
                Metric(
                    path=col["path"], reverse=col["order"] == self.DESCENDING
                )
                for col in self.extra_results_columns
                if not col.get("exclude_from_ranking", False)
            ],
        )

    @property
    def read_only_fields_for_dependent_phases(self):
        common_fields = ["submission_kind"]
        if self.submission_kind == SubmissionKindChoices.ALGORITHM:
            common_fields += ["algorithm_inputs", "algorithm_outputs"]
        return common_fields

    def _clean_parent_phase(self):
        if self.parent:
            if self.parent not in self.parent_phase_choices:
                raise ValidationError(
                    f"This phase cannot be selected as parent phase for the current "
                    f"phase. The parent phase needs to match the current phase in "
                    f"all of the following settings: "
                    f"{oxford_comma(self.read_only_fields_for_dependent_phases)}. "
                    f"The parent phase cannot have the current phase or any of "
                    f"the current phase's children set as its parent."
                )

            if self.parent.count_valid_archive_items < 1:
                raise ValidationError(
                    "The parent phase needs to have at least 1 valid archive item."
                )

            if (
                self.submissions_open_at
                and self.parent.submissions_open_at
                and self.submissions_open_at < self.parent.submissions_open_at
            ):
                raise ValidationError(SUBMISSION_WINDOW_PARENT_VALIDATION_TEXT)

    def set_default_interfaces(self):
        self.inputs.set(
            [ComponentInterface.objects.get(slug="predictions-csv-file")]
        )
        self.outputs.set(
            [ComponentInterface.objects.get(slug="metrics-json-file")]
        )

    def assign_permissions(self):
        assign_perm("view_phase", self.challenge.admins_group, self)
        assign_perm("change_phase", self.challenge.admins_group, self)
        assign_perm(
            "create_phase_submission", self.challenge.admins_group, self
        )

        if self.public:
            assign_perm(
                "create_phase_submission",
                self.challenge.participants_group,
                self,
            )
        else:
            remove_perm(
                "create_phase_submission",
                self.challenge.participants_group,
                self,
            )

    def get_absolute_url(self):
        return reverse(
            "pages:home",
            kwargs={"challenge_short_name": self.challenge.short_name},
        )

    @property
    def submission_limit_period_timedelta(self):
        return timedelta(days=self.submission_limit_period)

    def get_next_submission(self, *, user):
        """
        Determines the number of submissions left for the user,
        and when they can next submit.
        """
        now = timezone.now()

        if not self.open_for_submissions:
            remaining_submissions = 0
            next_sub_at = None

        else:
            filter_kwargs = {"creator": user}

            if self.submission_limit_period is not None:
                filter_kwargs.update(
                    {
                        "created__gte": now
                        - self.submission_limit_period_timedelta
                    }
                )

            evals_in_period = (
                self.submission_set.filter(**filter_kwargs)
                .exclude(evaluation__status=Evaluation.FAILURE)
                .distinct()
                .order_by("-created")
            )

            remaining_submissions = max(
                0,
                self.submissions_limit_per_user_per_period
                - evals_in_period.count(),
            )

            if remaining_submissions:
                next_sub_at = now
            elif (
                self.submissions_limit_per_user_per_period == 0
                or self.submission_limit_period is None
            ):
                # User is never going to be able to submit again
                next_sub_at = None
            else:
                next_sub_at = (
                    evals_in_period[
                        self.submissions_limit_per_user_per_period - 1
                    ].created
                    + self.submission_limit_period_timedelta
                )

        return {
            "remaining_submissions": remaining_submissions,
            "next_submission_at": next_sub_at,
        }

    def has_pending_evaluations(self, *, user_pks):
        return (
            Evaluation.objects.filter(
                submission__phase=self, submission__creator__pk__in=user_pks
            )
            .exclude(
                status__in=(
                    Evaluation.SUCCESS,
                    Evaluation.FAILURE,
                    Evaluation.CANCELLED,
                )
            )
            .exists()
        )

    def handle_submission_limit_avoidance(self, *, user):
        on_commit(
            deactivate_user.signature(kwargs={"user_pk": user.pk}).apply_async
        )
        mail_managers(
            subject="Suspected submission limit avoidance",
            message=format_html(
                (
                    "User '{username}' suspected of avoiding submission limits "
                    "for '{phase}' and was deactivated.\n\nSee:\n{vus_links}"
                ),
                username=user.username,
                phase=self,
                vus_links="\n".join(
                    vus.get_absolute_url()
                    for vus in VerificationUserSet.objects.filter(users=user)
                ),
            ),
        )

    @property
    def submission_period_is_open_now(self):
        now = timezone.now()
        upper_bound = self.submissions_close_at or now + timedelta(days=1)
        lower_bound = self.submissions_open_at or now - timedelta(days=1)
        return lower_bound < now < upper_bound

    @property
    def open_for_submissions(self):
        return (
            self.public
            and self.submission_period_is_open_now
            and self.submissions_limit_per_user_per_period > 0
            and self.challenge.available_compute_euro_millicents > 0
        )

    @property
    def status(self):
        now = timezone.now()
        if self.open_for_submissions:
            return StatusChoices.OPEN
        else:
            if self.submissions_open_at and now < self.submissions_open_at:
                return StatusChoices.OPENING_SOON
            elif self.submissions_close_at and now > self.submissions_close_at:
                return StatusChoices.COMPLETED
            else:
                return StatusChoices.CLOSED

    @property
    def submission_status_string(self):
        if self.status == StatusChoices.OPEN and self.submissions_close_at:
            return (
                f"Accepting submissions for {self.title} until "
                f'{localtime(self.submissions_close_at).strftime("%b %d %Y at %H:%M")}'
            )
        elif (
            self.status == StatusChoices.OPEN and not self.submissions_close_at
        ):
            return f"Accepting submissions for {self.title}"
        elif self.status == StatusChoices.OPENING_SOON:
            return (
                f"Opening submissions for {self.title} on "
                f'{localtime(self.submissions_open_at).strftime("%b %d %Y at %H:%M")}'
            )
        elif self.status == StatusChoices.COMPLETED:
            return f"{self.title} completed"
        elif self.status == StatusChoices.CLOSED:
            return "Not accepting submissions"
        else:
            raise NotImplementedError(f"{self.status} not implemented")

    @cached_property
    def active_image(self):
        """
        Returns
        -------
            The desired image version for this phase or None
        """
        try:
            return (
                self.method_set.executable_images()
                .filter(is_desired_version=True)
                .get()
            )
        except ObjectDoesNotExist:
            return None

    @cached_property
    def active_ground_truth(self):
        """
        Returns
        -------
            The desired ground truth version for this phase or None
        """
        try:
            return self.ground_truths.filter(is_desired_version=True).get()
        except ObjectDoesNotExist:
            return None

    @property
    def ground_truth_upload_in_progress(self):
        return self.ground_truths.filter(
            import_status__in=(ImportStatusChoices.INITIALIZED,)
        ).exists()

    @cached_property
    def valid_archive_items(self):
        """Returns the archive items that are valid for this phase"""
        if self.archive and self.algorithm_inputs:
            return self.archive.items.annotate(
                interface_match_count=Count(
                    "values",
                    filter=Q(
                        values__interface__in={*self.algorithm_inputs.all()}
                    ),
                )
            ).filter(interface_match_count=len(self.algorithm_inputs.all()))
        else:
            return ArchiveItem.objects.none()

    @cached_property
    def count_valid_archive_items(self):
        return self.valid_archive_items.count()

    def send_give_algorithm_editors_job_view_permissions_changed_email(self):
        message = format_html(
            (
                "You are being emailed as you are an admin of '{challenge}' "
                "and an important setting has been changed.\n\n"
                "The 'Give Algorithm Editors Job View Permissions' setting has "
                "been enabled for [{phase}]({phase_settings_url}).\n\n"
                "This means that editors of each algorithm submitted to this "
                "phase (i.e. the challenge participants) will automatically be "
                "given view permissions to their algorithm jobs and their logs.\n\n"
                "WARNING: This means that data in the linked archive is now "
                "accessible to the participants!\n\n"
                "You can update this setting in the [Phase Settings]({phase_settings_url})."
            ),
            challenge=self.challenge,
            phase=self.title,
            phase_settings_url=reverse(
                "evaluation:phase-update",
                kwargs={
                    "challenge_short_name": self.challenge.short_name,
                    "slug": self.slug,
                },
            ),
        )
        site = Site.objects.get_current()
        send_standard_email_batch(
            site=site,
            subject="WARNING: Permissions granted to Challenge Participants",
            markdown_message=message,
            recipients=self.challenge.admins_group.user_set.select_related(
                "user_profile"
            ).all(),
            subscription_type=EmailSubscriptionTypes.SYSTEM,
        )

    @cached_property
    def descendants(self):
        descendants = []
        children = self.children.all()
        for child in children:
            descendants.append(child)
            descendants.extend(child.descendants)
        return descendants

    @cached_property
    def parent_phase_choices(self):
        extra_filters = {}
        extra_annotations = {}
        if self.submission_kind == SubmissionKindChoices.ALGORITHM:
            algorithm_inputs = self.algorithm_inputs.all()
            algorithm_outputs = self.algorithm_outputs.all()
            extra_annotations = {
                "total_input_count": Count("algorithm_inputs", distinct=True),
                "total_output_count": Count(
                    "algorithm_outputs", distinct=True
                ),
                "relevant_input_count": Count(
                    "algorithm_inputs",
                    filter=Q(algorithm_inputs__in=algorithm_inputs),
                    distinct=True,
                ),
                "relevant_output_count": Count(
                    "algorithm_outputs",
                    filter=Q(algorithm_outputs__in=algorithm_outputs),
                    distinct=True,
                ),
            }
            extra_filters = {
                "total_input_count": len(algorithm_inputs),
                "total_output_count": len(algorithm_outputs),
                "relevant_input_count": len(algorithm_inputs),
                "relevant_output_count": len(algorithm_outputs),
            }
        return (
            Phase.objects.annotate(**extra_annotations)
            .filter(
                challenge=self.challenge,
                submission_kind=self.submission_kind,
                **extra_filters,
            )
            .exclude(
                pk=self.pk,
            )
            .exclude(
                parent__in=[self, *self.descendants],
            )
        )


class PhaseUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Phase, on_delete=models.CASCADE)


class PhaseGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Phase, on_delete=models.CASCADE)


class Method(UUIDModel, ComponentImage):
    """Store the methods for performing an evaluation."""

    phase = models.ForeignKey(Phase, on_delete=models.PROTECT, null=True)

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        assign_perm("view_method", self.phase.challenge.admins_group, self)
        assign_perm("change_method", self.phase.challenge.admins_group, self)

    def get_absolute_url(self):
        return reverse(
            "evaluation:method-detail",
            kwargs={
                "pk": self.pk,
                "challenge_short_name": self.phase.challenge.short_name,
                "slug": self.phase.slug,
            },
        )

    def get_peer_images(self):
        return Method.objects.filter(phase=self.phase)


class MethodUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Method, on_delete=models.CASCADE)


class MethodGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Method, on_delete=models.CASCADE)


def submission_file_path(instance, filename):
    # Must match the protected serving url
    return (
        f"{settings.EVALUATION_FILES_SUBDIRECTORY}/"
        f"{instance.phase.challenge.pk}/"
        f"submissions/"
        f"{instance.creator.pk}/"
        f"{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


def submission_supplementary_file_path(instance, filename):
    return (
        f"evaluation-supplementary/"
        f"{instance.phase.challenge.pk}/"
        f"{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


class Submission(UUIDModel):
    """Store files for evaluation."""

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    phase = models.ForeignKey(Phase, on_delete=models.PROTECT, null=True)
    algorithm_image = models.ForeignKey(
        AlgorithmImage, null=True, on_delete=models.PROTECT
    )
    algorithm_model = models.ForeignKey(
        AlgorithmModel, null=True, blank=True, on_delete=models.PROTECT
    )
    user_upload = models.ForeignKey(
        UserUpload, blank=True, null=True, on_delete=models.SET_NULL
    )
    predictions_file = models.FileField(
        upload_to=submission_file_path,
        validators=[
            MimeTypeValidator(
                allowed_types=(
                    "application/zip",
                    "text/plain",
                    "application/json",
                )
            ),
            ExtensionValidator(
                allowed_extensions=(
                    ".zip",
                    ".csv",
                    ".json",
                )
            ),
        ],
        storage=protected_s3_storage,
        blank=True,
    )
    supplementary_file = models.FileField(
        upload_to=submission_supplementary_file_path,
        storage=public_s3_storage,
        validators=[
            MimeTypeValidator(allowed_types=("text/plain", "application/pdf"))
        ],
        blank=True,
    )
    comment = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text=(
            "You can add a comment here to help you keep track of your "
            "submissions."
        ),
    )
    supplementary_url = models.URLField(
        blank=True, help_text="A URL associated with this submission."
    )

    class Meta:
        unique_together = (
            (
                "phase",
                "predictions_file",
                "algorithm_image",
                "algorithm_model",
            ),
        )

    @cached_property
    def is_evaluated_with_active_image_and_ground_truth(self):
        active_image = self.phase.active_image
        active_ground_truth = self.phase.active_ground_truth
        if active_image:
            return Evaluation.objects.filter(
                submission=self,
                method=active_image,
                ground_truth=active_ground_truth,
            ).exists()
        else:
            # No active image, so nothing to do to evaluate with it
            return True

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()
            if not is_following(self.creator, self.phase):
                follow(
                    user=self.creator,
                    obj=self.phase,
                    actor_only=False,
                    send_action=False,
                )
            e = create_evaluation.signature(
                kwargs={"submission_pk": self.pk}, immutable=True
            )
            on_commit(e.apply_async)

    def assign_permissions(self):
        assign_perm("view_submission", self.phase.challenge.admins_group, self)

        if self.phase.public:
            assign_perm("view_submission", self.creator, self)
        else:
            remove_perm("view_submission", self.creator, self)

    def get_absolute_url(self):
        return reverse(
            "evaluation:submission-detail",
            kwargs={
                "pk": self.pk,
                "challenge_short_name": self.phase.challenge.short_name,
                "slug": self.phase.slug,
            },
        )


class SubmissionUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Submission, on_delete=models.CASCADE)


class SubmissionGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Submission, on_delete=models.CASCADE)


def ground_truth_path(instance, filename):
    return (
        f"ground_truths/"
        f"{instance._meta.app_label.lower()}/"
        f"{instance._meta.model_name.lower()}/"
        f"{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


class EvaluationGroundTruth(Tarball):
    phase = models.ForeignKey(
        Phase, on_delete=models.PROTECT, related_name="ground_truths"
    )
    ground_truth = models.FileField(
        blank=True,
        upload_to=ground_truth_path,
        validators=[ExtensionValidator(allowed_extensions=(".tar.gz",))],
        help_text=(
            ".tar.gz file of the ground truth that will be extracted to /opt/ml/input/data/ground_truth/ during inference"
        ),
        storage=private_s3_storage,
    )

    @property
    def linked_file(self):
        return self.ground_truth

    def assign_permissions(self):
        # Challenge admins can view this ground truth
        assign_perm(
            f"view_{self._meta.model_name}",
            self.phase.challenge.admins_group,
            self,
        )
        # Challenge admins can change this ground truth
        assign_perm(
            f"change_{self._meta.model_name}",
            self.phase.challenge.admins_group,
            self,
        )

    def get_peer_tarballs(self):
        return EvaluationGroundTruth.objects.filter(phase=self.phase).exclude(
            pk=self.pk
        )

    def get_absolute_url(self):
        return reverse(
            "evaluation:ground-truth-detail",
            kwargs={
                "slug": self.phase.slug,
                "pk": self.pk,
                "challenge_short_name": self.phase.challenge.short_name,
            },
        )


class EvaluationGroundTruthUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(
        EvaluationGroundTruth, on_delete=models.CASCADE
    )


class EvaluationGroundTruthGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(
        EvaluationGroundTruth, on_delete=models.CASCADE
    )


class Evaluation(UUIDModel, ComponentJob):
    """Stores information about a evaluation for a given submission."""

    submission = models.ForeignKey("Submission", on_delete=models.PROTECT)
    method = models.ForeignKey("Method", on_delete=models.PROTECT)
    ground_truth = models.ForeignKey(
        EvaluationGroundTruth, null=True, blank=True, on_delete=models.PROTECT
    )

    published = models.BooleanField(default=True, db_index=True)
    rank = models.PositiveIntegerField(
        default=0,
        help_text=(
            "The position of this result on the leaderboard. If the value is "
            "zero, then the result is unranked."
        ),
        db_index=True,
    )
    rank_score = models.FloatField(default=0.0)
    rank_per_metric = models.JSONField(default=dict)

    class Meta(UUIDModel.Meta, ComponentJob.Meta):
        unique_together = ("submission", "method", "ground_truth")

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.published = self.submission.phase.auto_publish_new_results

        super().save(*args, **kwargs)

        self.assign_permissions()

        on_commit(
            lambda: calculate_ranks.apply_async(
                kwargs={"phase_pk": self.submission.phase.pk}
            )
        )

    @property
    def title(self):
        return f"#{self.rank} {self.submission.creator.username}"

    def assign_permissions(self):
        admins_group = self.submission.phase.challenge.admins_group
        assign_perm("view_evaluation", admins_group, self)
        assign_perm("change_evaluation", admins_group, self)

        all_user_group = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )
        all_users_can_view = (
            self.published
            and self.submission.phase.public
            and not self.submission.phase.challenge.hidden
        )
        if all_users_can_view:
            assign_perm("view_evaluation", all_user_group, self)
        else:
            remove_perm("view_evaluation", all_user_group, self)

        participants_can_view = (
            self.published
            and self.submission.phase.public
            and self.submission.phase.challenge.hidden
        )
        participants_group = self.submission.phase.challenge.participants_group
        if participants_can_view:
            assign_perm("view_evaluation", participants_group, self)
        else:
            remove_perm("view_evaluation", participants_group, self)

    @property
    def container(self):
        return self.method

    @property
    def output_interfaces(self):
        return self.submission.phase.outputs

    @property
    def executor_kwargs(self):
        executor_kwargs = super().executor_kwargs
        if self.ground_truth:
            executor_kwargs["ground_truth"] = self.ground_truth.ground_truth
        return executor_kwargs

    @cached_property
    def metrics_json_file(self):
        for output in self.outputs.all():
            if output.interface.slug == "metrics-json-file":
                return output.value

    @cached_property
    def invalid_metrics(self):
        return {
            metric.path
            for metric in self.submission.phase.valid_metrics
            if not isinstance(
                get_jsonpath(self.metrics_json_file, metric.path), (int, float)
            )
        }

    def clean(self):
        if self.submission.phase != self.method.phase:
            raise ValidationError(
                "The submission and method phases should"
                "be the same. You are trying to evaluate a"
                f"submission for {self.submission.phase}"
                f"with a method for {self.method.phase}"
            )

        super().clean()

    def update_status(self, *args, **kwargs):
        res = super().update_status(*args, **kwargs)

        if self.status == self.FAILURE:
            Notification.send(
                kind=NotificationType.NotificationTypeChoices.EVALUATION_STATUS,
                actor=self.submission.creator,
                message="failed",
                action_object=self,
                target=self.submission.phase,
            )

        if self.status == self.SUCCESS:
            Notification.send(
                kind=NotificationType.NotificationTypeChoices.EVALUATION_STATUS,
                actor=self.submission.creator,
                message="succeeded",
                action_object=self,
                target=self.submission.phase,
            )

        return res

    def get_absolute_url(self):
        return reverse(
            "evaluation:detail",
            kwargs={
                "pk": self.pk,
                "challenge_short_name": self.submission.phase.challenge.short_name,
            },
        )


class EvaluationUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Evaluation, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        raise RuntimeError(
            "User permissions should not be assigned for this model"
        )


class EvaluationGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Evaluation, on_delete=models.CASCADE)


class CombinedLeaderboard(TitleSlugDescriptionModel, UUIDModel):
    class CombinationMethodChoices(models.TextChoices):
        MEAN = "MEAN", "Mean"
        MEDIAN = "MEDIAN", "Median"
        SUM = "SUM", "Sum"

    challenge = models.ForeignKey(
        Challenge, on_delete=models.PROTECT, editable=False
    )
    phases = models.ManyToManyField(Phase, through="CombinedLeaderboardPhase")
    combination_method = models.CharField(
        max_length=6,
        choices=CombinationMethodChoices.choices,
        default=CombinationMethodChoices.MEAN,
    )

    class Meta:
        unique_together = (("challenge", "slug"),)

    @cached_property
    def public_phases(self):
        return self.phases.filter(public=True)

    @property
    def concrete_combination_method(self):
        if self.combination_method == self.CombinationMethodChoices.MEAN:
            return mean
        elif self.combination_method == self.CombinationMethodChoices.MEDIAN:
            return median
        elif self.combination_method == self.CombinationMethodChoices.SUM:
            return sum
        else:
            raise NotImplementedError

    @cached_property
    def _combined_ranks_object(self):
        result = cache.get(self.combined_ranks_cache_key)

        if (
            result is None
            or result["phases"] != {phase.pk for phase in self.public_phases}
            or result["combination_method"] != self.combination_method
        ):
            self.schedule_combined_ranks_update()
            return None
        else:
            return result

    @property
    def combined_ranks(self):
        combined_ranks = self._combined_ranks_object
        if combined_ranks is not None:
            return combined_ranks["results"]
        else:
            return []

    @property
    def combined_ranks_users(self):
        return [cr["user"] for cr in self.combined_ranks]

    @property
    def combined_ranks_created(self):
        combined_ranks = self._combined_ranks_object
        if combined_ranks is not None:
            return combined_ranks["created"]
        else:
            return None

    @property
    def users_best_evaluation_per_phase(self):
        evaluations = Evaluation.objects.filter(
            # Note, only use public phases here to prevent leaking of
            # evaluations for hidden phases
            submission__phase__in=self.public_phases,
            published=True,
            status=Evaluation.SUCCESS,
            rank__gt=0,
        ).values(
            "submission__creator__username",
            "submission__phase__pk",
            "pk",
            "created",
            "rank",
        )

        users_best_evaluation_per_phase = {}

        for evaluation in evaluations.iterator():
            phase = evaluation["submission__phase__pk"]
            user = evaluation["submission__creator__username"]

            if user not in users_best_evaluation_per_phase:
                users_best_evaluation_per_phase[user] = {}

            if (
                phase not in users_best_evaluation_per_phase[user]
                or evaluation["rank"]
                < users_best_evaluation_per_phase[user][phase]["rank"]
            ):
                users_best_evaluation_per_phase[user][phase] = {
                    "pk": evaluation["pk"],
                    "created": evaluation["created"],
                    "rank": evaluation["rank"],
                }

        return users_best_evaluation_per_phase

    @property
    def combined_ranks_cache_key(self):
        return f"{self._meta.app_label}.{self._meta.model_name}.combined_ranks.{self.pk}"

    def update_combined_ranks_cache(self):
        combined_ranks = []
        num_phases = self.public_phases.count()

        now = timezone.now()
        for user, evaluations in self.users_best_evaluation_per_phase.items():
            if len(evaluations) == num_phases:  # Exclude missing data
                combined_ranks.append(
                    {
                        "user": user,
                        "combined_rank": self.concrete_combination_method(
                            evaluation["rank"]
                            for evaluation in evaluations.values()
                        ),
                        "created": max(
                            evaluation["created"]
                            for evaluation in evaluations.values()
                        ),
                        "evaluations": {
                            phase: {
                                "pk": evaluation["pk"],
                                "rank": evaluation["rank"],
                            }
                            for phase, evaluation in evaluations.items()
                        },
                    }
                )

        self._rank_combined_rank_scores(combined_ranks)

        cache_object = {
            "phases": {phase.pk for phase in self.public_phases},
            "combination_method": self.combination_method,
            "created": now,
            "results": combined_ranks,
        }

        cache.set(self.combined_ranks_cache_key, cache_object, timeout=None)

    @staticmethod
    def _rank_combined_rank_scores(combined_ranks):
        """In-place addition of a rank based on the combined rank"""
        combined_ranks.sort(key=lambda x: x["combined_rank"])
        current_score = current_rank = None

        for idx, score in enumerate(
            cr["combined_rank"] for cr in combined_ranks
        ):
            if score != current_score:
                current_score = score
                current_rank = idx + 1

            combined_ranks[idx]["rank"] = current_rank

    def schedule_combined_ranks_update(self):
        on_commit(
            update_combined_leaderboard.signature(
                kwargs={"pk": self.pk}
            ).apply_async
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.schedule_combined_ranks_update()

    def get_absolute_url(self):
        return reverse(
            "evaluation:combined-leaderboard-detail",
            kwargs={
                "challenge_short_name": self.challenge.short_name,
                "slug": self.slug,
            },
        )

    def delete(self, *args, **kwargs):
        cache.delete(self.combined_ranks_cache_key)
        return super().delete(*args, **kwargs)


class CombinedLeaderboardPhase(models.Model):
    # Through table for the combined leaderboard
    # https://docs.djangoproject.com/en/4.2/topics/db/models/#intermediary-manytomany
    phase = models.ForeignKey(Phase, on_delete=models.CASCADE)
    combined_leaderboard = models.ForeignKey(
        CombinedLeaderboard, on_delete=models.CASCADE
    )


class OptionalHangingProtocolPhase(models.Model):
    # Through table for optional hanging protocols
    # https://docs.djangoproject.com/en/4.2/topics/db/models/#intermediary-manytomany
    phase = models.ForeignKey(Phase, on_delete=models.CASCADE)
    hanging_protocol = models.ForeignKey(
        "hanging_protocols.HangingProtocol", on_delete=models.CASCADE
    )
