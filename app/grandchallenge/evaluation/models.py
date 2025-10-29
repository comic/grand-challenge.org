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
from django.db.models.functions import Coalesce
from django.db.transaction import on_commit
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.text import get_valid_filename
from django.utils.timezone import localtime
from django_extensions.db.fields import AutoSlugField
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.algorithms.models import (
    AlgorithmImage,
    AlgorithmInterface,
    AlgorithmModel,
    Job,
)
from grandchallenge.archives.models import Archive
from grandchallenge.challenges.models import Challenge
from grandchallenge.components.models import (
    CIVForObjectMixin,
    ComponentImage,
    ComponentInterface,
    ComponentJob,
    ComponentJobManager,
    ImportStatusChoices,
    Tarball,
)
from grandchallenge.components.schemas import (
    SELECTABLE_GPU_TYPES_SCHEMA,
    GPUTypeChoices,
    get_default_gpu_type_choices,
)
from grandchallenge.core.guardian import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
)
from grandchallenge.core.models import (
    FieldChangeMixin,
    TitleSlugDescriptionModel,
    UUIDModel,
)
from grandchallenge.core.storage import (
    private_s3_storage,
    protected_s3_storage,
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
    check_prerequisites_for_evaluation_execution,
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
from grandchallenge.notifications.models import (
    Notification,
    NotificationTypeChoices,
)
from grandchallenge.profiles.models import EmailSubscriptionTypes
from grandchallenge.profiles.tasks import deactivate_user
from grandchallenge.subdomains.utils import reverse
from grandchallenge.uploads.models import UserUpload
from grandchallenge.utilization.models import EvaluationUtilization
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


def get_archive_items_for_interfaces(*, algorithm_interfaces, archive_items):
    valid_archive_items_per_interface = {}
    for interface in algorithm_interfaces:
        inputs = interface.inputs.all()
        valid_archive_items_per_interface[interface] = (
            archive_items.annotate(
                input_count=Count("values", distinct=True),
                relevant_input_count=Count(
                    "values",
                    filter=Q(values__interface__in=inputs),
                    distinct=True,
                ),
            )
            .filter(input_count=len(inputs), relevant_input_count=len(inputs))
            .prefetch_related("values")
        )
    return valid_archive_items_per_interface


def get_valid_jobs_for_interfaces_and_archive_items(
    *,
    algorithm_image,
    algorithm_interfaces,
    valid_archive_items_per_interface,
    algorithm_model=None,
    subset_by_status=None,
):
    if algorithm_model:
        extra_filter = {"algorithm_model": algorithm_model}
    else:
        extra_filter = {"algorithm_model__isnull": True}

    if subset_by_status:
        extra_filter["status__in"] = subset_by_status

    jobs = Job.objects.filter(
        algorithm_image=algorithm_image,
        creator=None,
        **extra_filter,
    )

    jobs_per_interface = {}
    for interface in algorithm_interfaces:
        jobs_per_interface[interface] = []
        jobs_for_interface = (
            jobs.filter(
                algorithm_interface=interface,
                inputs__archive_items__in=valid_archive_items_per_interface[
                    interface
                ],
            )
            .distinct()
            .prefetch_related("inputs")
            .select_related("algorithm_image__algorithm")
        )

        archive_item_value_sets = {
            frozenset(value.pk for value in item.values.all())
            for item in valid_archive_items_per_interface[interface]
        }

        for job in jobs_for_interface:
            # subset to jobs whose input set exactly matches
            # one of the valid archive items' value sets
            if (
                frozenset(inpt.pk for inpt in job.inputs.all())
                in archive_item_value_sets
            ):
                jobs_per_interface[interface].append(job)

    return jobs_per_interface


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
        max_length=64,
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
    submission_page_markdown = models.TextField(
        blank=True,
        help_text=(
            "Markdown to include on the submission page to provide "
            "more context to users making a submission to the phase."
        ),
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
            "If True, the entire contents of metrics.json is available "
            "on the results detail page and over the API. "
            "If False, only the metrics used for ranking are available "
            "on the results detail page and over the API. "
            "Challenge administrators can always access the full "
            "metrics.json over the API."
        ),
    )
    algorithm_interfaces = models.ManyToManyField(
        to=AlgorithmInterface,
        through="evaluation.PhaseAlgorithmInterface",
        blank=True,
        help_text="The interfaces that an algorithm for this phase must implement.",
    )
    additional_evaluation_inputs = models.ManyToManyField(
        to=ComponentInterface,
        through="evaluation.PhaseAdditionalEvaluationInput",
        related_name="additional_eval_inputs",
        blank=True,
    )
    evaluation_outputs = models.ManyToManyField(
        to=ComponentInterface,
        related_name="eval_outputs",
        through="evaluation.PhaseEvaluationOutput",
    )
    algorithm_selectable_gpu_type_choices = models.JSONField(
        default=get_default_gpu_type_choices,
        help_text=(
            "The GPU type choices that participants will be able to select for their "
            "algorithm inference jobs. The setting on the algorithm will be "
            "validated against this on submission. Options are "
            f"{GPUTypeChoices.values}.".replace("'", '"')
        ),
        validators=[JSONValidator(schema=SELECTABLE_GPU_TYPES_SCHEMA)],
    )
    algorithm_maximum_settable_memory_gb = models.PositiveSmallIntegerField(
        default=settings.ALGORITHMS_MAX_MEMORY_GB,
        help_text=(
            "Maximum amount of main memory (DRAM) that participants will be allowed to "
            "assign to algorithm inference jobs for submission. The setting on the "
            "algorithm will be validated against this on submission."
        ),
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
    evaluation_selectable_gpu_type_choices = models.JSONField(
        default=get_default_gpu_type_choices,
        help_text=(
            "The GPU type choices that challenge admins will be able to set for the "
            f"evaluation method. Options are {GPUTypeChoices.values}.".replace(
                "'", '"'
            )
        ),
        validators=[JSONValidator(schema=SELECTABLE_GPU_TYPES_SCHEMA)],
    )
    evaluation_requires_gpu_type = models.CharField(
        max_length=4,
        blank=True,
        default=GPUTypeChoices.NO_GPU,
        choices=GPUTypeChoices.choices,
        help_text=(
            "What GPU to attach to this phases evaluations. "
            "Note that the GPU attached to any algorithm inference jobs "
            "is determined by the submitted algorithm."
        ),
    )
    evaluation_maximum_settable_memory_gb = models.PositiveSmallIntegerField(
        default=settings.ALGORITHMS_MAX_MEMORY_GB,
        help_text=(
            "Maximum amount of main memory (DRAM) that challenge admins will be able to "
            "assign for the evaluation method."
        ),
    )
    evaluation_requires_memory_gb = models.PositiveSmallIntegerField(
        default=8,
        help_text=(
            "How much main memory (DRAM) to assign to this phases evaluations. "
            "Note that the memory assigned to any algorithm inference jobs "
            "is determined by the submitted algorithm."
        ),
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
    external_evaluation = models.BooleanField(
        default=False,
        help_text=(
            "Are submissions to this phase evaluated externally? "
            "If so, it is the responsibility of the external service to "
            "claim and evaluate new submissions, download the submitted "
            "algorithm models and images and return the results."
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

    def save(self, *args, skip_calculate_ranks=False, **kwargs):
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

        if not skip_calculate_ranks:
            on_commit(
                calculate_ranks.signature(
                    kwargs={"phase_pk": self.pk}
                ).apply_async
            )

    def clean(self):
        super().clean()
        self._clean_submission_kind()
        self._clean_algorithm_submission_settings()
        self._clean_submission_limits()
        self._clean_parent_phase()
        self._clean_external_evaluation()
        self._clean_evaluation_requirements()

    def _clean_submission_kind(self):
        if self.has_changed("submission_kind"):
            if self.submission_set.exists():
                raise ValidationError(
                    "Cannot change submission kind of Phase with existing submissions"
                )

    def _clean_algorithm_submission_settings(self):
        if self.submission_kind == SubmissionKindChoices.ALGORITHM:
            if (
                self.submissions_limit_per_user_per_period > 0
                and not self.external_evaluation
                and (not self.archive or not self.algorithm_interfaces)
            ):
                raise ValidationError(
                    format_html(
                        (
                            "To change the submission limit to above 0, you need to first link an archive containing the secret "
                            "test data to this phase and define the interfaces (input-output combinations) that the submitted algorithms need to "
                            "read/write. To configure these settings, please get in touch with {support_email}."
                        ),
                        support_email=settings.SUPPORT_EMAIL,
                    )
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
            and not self.external_evaluation
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

    def _clean_external_evaluation(self):
        if self.external_evaluation:
            if self.method_set.exists():
                raise ValidationError(
                    "Phases that have an evaluation method cannot be turned "
                    "into external evaluation phases. Remove the method and "
                    "try again."
                )
            if not self.submission_kind == SubmissionKindChoices.ALGORITHM:
                raise ValidationError(
                    "External evaluation is only possible for algorithm submission phases."
                )
            if not self.parent:
                raise ValidationError(
                    "An external evaluation phase must have a parent phase."
                )

    def _clean_evaluation_requirements(self):
        if (
            self.evaluation_requires_gpu_type
            not in self.evaluation_selectable_gpu_type_choices
        ):
            raise ValidationError(
                f"{self.evaluation_requires_gpu_type!r} is not a valid choice "
                f"for Evaluation requires gpu type. Either change the choice or "
                f"add it to the list of selectable gpu types."
            )
        if (
            self.evaluation_requires_memory_gb
            > self.evaluation_maximum_settable_memory_gb
        ):
            raise ValidationError(
                f"Ensure the value for Evaluation requires memory gb (currently "
                f"{self.evaluation_requires_memory_gb}) is less than or equal "
                f"to the maximum settable (currently "
                f"{self.evaluation_maximum_settable_memory_gb})."
            )

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

    @property
    def algorithm_interfaces_locked(self):
        if self.parent or self.children.exists():
            return True
        else:
            return False

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
        return ["submission_kind"]

    def _clean_parent_phase(self):
        if self.parent:
            if self.parent not in self.parent_phase_choices:
                raise ValidationError(
                    f"This phase cannot be selected as parent phase for the current "
                    f"phase. The parent phase needs to match the current phase in "
                    f"all of the following settings: algorithm interfaces, "
                    f"{oxford_comma(self.read_only_fields_for_dependent_phases)}. "
                    f"The parent phase cannot have the current phase or any of "
                    f"the current phase's children set as its parent."
                )

            if self.parent.jobs_to_schedule_per_submission < 1:
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
        self.evaluation_outputs.set(
            [ComponentInterface.objects.get(slug="metrics-json-file")]
        )

    @cached_property
    def linked_component_interfaces(self):
        return (
            ComponentInterface.objects.filter(
                Q(inputs__in=self.algorithm_interfaces.all())
                | Q(outputs__in=self.algorithm_interfaces.all())
            )
            .distinct()
            .order_by("pk")
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

    def has_active_evaluations(self, *, users):
        return (
            Evaluation.objects.active()
            .filter(
                submission__phase=self,
                submission__creator__in=users,
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
    def valid_archive_items_per_interface(self):
        """
        Returns the archive items that are valid for
        each interface configured for this phase
        """
        if self.archive and self.algorithm_interfaces:
            return get_archive_items_for_interfaces(
                algorithm_interfaces=self.algorithm_interfaces.prefetch_related(
                    "inputs"
                ),
                archive_items=self.archive.items.prefetch_related(
                    "values__interface"
                ),
            )
        else:
            return {}

    @cached_property
    def valid_archive_item_count_per_interface(self):
        return {
            interface: len(valid_archive_items)
            for interface, valid_archive_items in self.valid_archive_items_per_interface.items()
        }

    @cached_property
    def jobs_to_schedule_per_submission(self):
        return sum(self.valid_archive_item_count_per_interface.values())

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
            algorithm_interfaces = self.algorithm_interfaces.all()
            extra_annotations = {
                "total_interface_count": Count(
                    "algorithm_interfaces", distinct=True
                ),
                "relevant_interface_count": Count(
                    "algorithm_interfaces",
                    filter=Q(algorithm_interfaces__in=algorithm_interfaces),
                    distinct=True,
                ),
            }
            extra_filters = {
                "total_interface_count": len(algorithm_interfaces),
                "relevant_interface_count": len(algorithm_interfaces),
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

    @property
    def algorithm_interface_manager(self):
        return self.algorithm_interfaces

    @property
    def algorithm_interface_through_model_manager(self):
        return PhaseAlgorithmInterface.objects.filter(phase=self)

    @property
    def additional_inputs_field(self):
        return self.additional_evaluation_inputs

    @property
    def additional_outputs_field(self):
        return self.evaluation_outputs

    @property
    def algorithm_interface_create_url(self):
        return reverse(
            "evaluation:interface-create",
            kwargs={"challenge_short_name": self.challenge, "slug": self.slug},
        )

    @property
    def algorithm_interface_delete_viewname(self):
        return "evaluation:interface-delete"

    @property
    def algorithm_interface_list_url(self):
        return reverse(
            "evaluation:interface-list",
            kwargs={"challenge_short_name": self.challenge, "slug": self.slug},
        )


class CheckForOverlappingSocketsMixin:
    def clean(self):
        super().clean()

        if self.phase.submission_kind == SubmissionKindChoices.ALGORITHM:
            algorithm_socket_slugs = set(
                self.phase.algorithm_interfaces.values_list(
                    "inputs__slug", flat=True
                )
            ) | set(
                self.phase.algorithm_interfaces.values_list(
                    "outputs__slug", flat=True
                )
            )

            if self.socket.slug in algorithm_socket_slugs:
                raise ValidationError(
                    f"{self.socket.slug} cannot be defined as evaluation "
                    f"inputs or outputs because it is already defined as "
                    f"algorithm input or output for this phase"
                )


class PhaseAdditionalEvaluationInput(
    CheckForOverlappingSocketsMixin, models.Model
):
    socket = models.ForeignKey(ComponentInterface, on_delete=models.CASCADE)
    phase = models.ForeignKey(Phase, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["phase", "socket"],
                name="unique_phase_input_combination",
            ),
        ]

    def clean(self):
        super().clean()

        from grandchallenge.algorithms.forms import RESERVED_SOCKET_SLUGS

        if self.socket.slug in RESERVED_SOCKET_SLUGS:
            raise ValidationError(
                f'Evaluation inputs cannot be of the following types: {", ".join(RESERVED_SOCKET_SLUGS)}'
            )


class PhaseEvaluationOutput(CheckForOverlappingSocketsMixin, models.Model):
    socket = models.ForeignKey(ComponentInterface, on_delete=models.CASCADE)
    phase = models.ForeignKey(Phase, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["phase", "socket"],
                name="unique_phase_output_combination",
            ),
        ]


class PhaseUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Phase, on_delete=models.CASCADE)


class PhaseGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset(
        {"create_phase_submission", "view_phase", "change_phase"}
    )

    content_object = models.ForeignKey(Phase, on_delete=models.CASCADE)


class PhaseAlgorithmInterface(models.Model):
    phase = models.ForeignKey(Phase, on_delete=models.CASCADE)
    interface = models.ForeignKey(AlgorithmInterface, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["phase", "interface"],
                name="unique_phase_interface_combination",
            ),
        ]


class Method(UUIDModel, ComponentImage):
    """Store the methods for performing an evaluation."""

    phase = models.ForeignKey(Phase, on_delete=models.PROTECT, null=True)

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def clean(self):
        cleaned_data = super().clean()
        if self.phase.external_evaluation:
            raise ValidationError(
                "You cannot add a method to an external evaluation."
            )
        return cleaned_data

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

    @property
    def import_status_url(self) -> str:
        return reverse(
            "evaluation:method-import-status-detail",
            kwargs={
                "pk": self.pk,
                "challenge_short_name": self.phase.challenge.short_name,
                "slug": self.phase.slug,
            },
        )

    def get_peer_images(self):
        return Method.objects.filter(phase=self.phase)


class MethodUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Method, on_delete=models.CASCADE)


class MethodGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset({"view_method", "change_method"})

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
    # Must match the protected serving url
    return (
        f"{settings.EVALUATION_SUPPLEMENTARY_FILES_SUBDIRECTORY}/"
        f"{instance.phase.challenge.pk}/"
        f"{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


class Submission(FieldChangeMixin, UUIDModel):
    """Store files for evaluation."""

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    phase = models.ForeignKey(Phase, on_delete=models.PROTECT)
    algorithm_image = models.ForeignKey(
        AlgorithmImage, null=True, on_delete=models.PROTECT
    )
    algorithm_model = models.ForeignKey(
        AlgorithmModel, null=True, blank=True, on_delete=models.PROTECT
    )
    algorithm_requires_gpu_type = models.CharField(
        editable=False,
        max_length=4,
        choices=GPUTypeChoices.choices,
        help_text="What GPU, if any, is required by the algorithm jobs?",
    )
    algorithm_requires_memory_gb = models.PositiveSmallIntegerField(
        editable=False,
        help_text="How much main memory (DRAM) is required by the algorithm jobs?",
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
        storage=protected_s3_storage,
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
        indexes = [
            models.Index(fields=["created"]),
        ]

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

        if not adding:
            for field in (
                "algorithm_requires_gpu_type",
                "algorithm_requires_memory_gb",
            ):
                if self.has_changed(field):
                    raise ValueError(f"{field} cannot be changed")

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

    def create_evaluation(self, *, additional_inputs):
        if (
            self.phase.additional_evaluation_inputs.exists()
            and not additional_inputs
        ):
            raise RuntimeError(
                "Additional inputs are required to create an evaluation for this phase"
            )

        if self.phase.external_evaluation:
            evaluation, created = Evaluation.objects.get_or_create(
                submission=self,
                defaults={
                    "time_limit": self.phase.evaluation_time_limit,
                    "requires_gpu_type": self.phase.evaluation_requires_gpu_type,
                    "requires_memory_gb": self.phase.evaluation_requires_memory_gb,
                },
            )
            if not created:
                logger.info(
                    "External evaluation already created for this submission."
                )
            return
        else:
            method = self.phase.active_image
            ground_truth = self.phase.active_ground_truth

            if not method:
                logger.error("No method ready for this submission")
                Notification.send(
                    kind=NotificationTypeChoices.MISSING_METHOD,
                    message="missing method",
                    actor=self.creator,
                    action_object=self,
                    target=self.phase,
                )
                return

            if Evaluation.objects.get_evaluations_with_same_inputs(
                inputs=additional_inputs if additional_inputs else [],
                submission=self,
                method=method,
                ground_truth=ground_truth,
                time_limit=self.phase.evaluation_time_limit,
                requires_gpu_type=self.phase.evaluation_requires_gpu_type,
                requires_memory_gb=self.phase.evaluation_requires_memory_gb,
            ):
                logger.error(
                    "Evaluation already created for this submission, method, ground truth and inputs."
                )
                return

            evaluation = Evaluation.objects.create(
                submission=self,
                method=method,
                ground_truth=ground_truth,
                time_limit=self.phase.evaluation_time_limit,
                requires_gpu_type=self.phase.evaluation_requires_gpu_type,
                requires_memory_gb=self.phase.evaluation_requires_memory_gb,
                status=Evaluation.VALIDATING_INPUTS,
            )

        if self.phase.submission_kind == SubmissionKindChoices.ALGORITHM:
            if not self.has_matching_algorithm_interfaces:
                evaluation.update_status(
                    status=Evaluation.CANCELLED,
                    error_message="The algorithm interfaces do not match those defined for the phase.",
                )

        if additional_inputs:
            evaluation.validate_civ_data_objects_and_execute_linked_task(
                civ_data_objects=additional_inputs, user=self.creator
            )
        else:
            e = check_prerequisites_for_evaluation_execution.signature(
                kwargs={"evaluation_pk": evaluation.pk}, immutable=True
            )
            on_commit(e.apply_async)

    def assign_permissions(self):
        assign_perm("view_submission", self.phase.challenge.admins_group, self)
        if self.phase.external_evaluation:
            external_evaluators_group = (
                self.phase.challenge.external_evaluators_group
            )
            if self.algorithm_image:
                assign_perm(
                    "download_algorithmimage",
                    external_evaluators_group,
                    self.algorithm_image,
                )
            if self.algorithm_model:
                assign_perm(
                    "download_algorithmmodel",
                    external_evaluators_group,
                    self.algorithm_model,
                )

        if self.creator:
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

    @cached_property
    def has_matching_algorithm_interfaces(self):
        algorithm_interfaces = set(
            self.algorithm_image.algorithm.interfaces.all()
        )
        phase_algorithm_interfaces = set(self.phase.algorithm_interfaces.all())
        return phase_algorithm_interfaces <= algorithm_interfaces


class SubmissionUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset({"view_submission"})

    content_object = models.ForeignKey(Submission, on_delete=models.CASCADE)


class SubmissionGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset({"view_submission"})

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

    @property
    def import_status_url(self) -> str:
        return reverse(
            "evaluation:ground-truth-import-status-detail",
            kwargs={
                "slug": self.phase.slug,
                "pk": self.pk,
                "challenge_short_name": self.phase.challenge.short_name,
            },
        )


class EvaluationGroundTruthUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(
        EvaluationGroundTruth, on_delete=models.CASCADE
    )


class EvaluationGroundTruthGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset(
        {"change_evaluationgroundtruth", "view_evaluationgroundtruth"}
    )

    content_object = models.ForeignKey(
        EvaluationGroundTruth, on_delete=models.CASCADE
    )


class EvaluationManager(ComponentJobManager):
    def get_evaluations_with_same_inputs(
        self,
        *,
        inputs,
        submission,
        method,
        ground_truth,
        time_limit,
        requires_gpu_type,
        requires_memory_gb,
    ):
        existing_civs = self.retrieve_existing_civs(civ_data_objects=inputs)
        unique_kwargs = {
            "submission": submission,
            "method": method,
            "time_limit": time_limit,
            "requires_gpu_type": requires_gpu_type,
            "requires_memory_gb": requires_memory_gb,
        }

        if ground_truth:
            unique_kwargs["ground_truth"] = ground_truth
        else:
            unique_kwargs["ground_truth__isnull"] = True

        input_interface_count = len(inputs)
        configured_input_interface_slugs = (
            submission.phase.additional_evaluation_inputs.values_list(
                "slug", flat=True
            )
        )

        # annotate the number of inputs and the number of inputs that match
        # the existing civs and filter on both counts so as to not include evaluations
        # with partially overlapping inputs
        # or evaluations with more inputs than the existing civs
        existing_evaluations = (
            Evaluation.objects.filter(**unique_kwargs)
            .annotate(
                additional_input_count=Coalesce(
                    Count(
                        "inputs",
                        filter=(
                            Q(
                                inputs__interface__slug__in=configured_input_interface_slugs
                            )
                        ),
                        distinct=True,
                    ),
                    0,
                ),
                relevant_additional_input_count=Coalesce(
                    Count(
                        "inputs",
                        filter=(Q(inputs__in=existing_civs)),
                        distinct=True,
                    ),
                    0,
                ),
            )
            .filter(
                additional_input_count=input_interface_count,
                relevant_additional_input_count=input_interface_count,
            )
        )

        return existing_evaluations


class Evaluation(CIVForObjectMixin, ComponentJob):
    """Stores information about a evaluation for a given submission."""

    submission = models.ForeignKey("Submission", on_delete=models.PROTECT)
    method = models.ForeignKey(
        "Method", null=True, blank=True, on_delete=models.PROTECT
    )
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
    claimed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="claimed_evaluations",
    )
    claimed_at = models.DateTimeField(null=True)

    objects = EvaluationManager.as_manager()

    class Meta(UUIDModel.Meta, ComponentJob.Meta):
        permissions = [("claim_evaluation", "Can claim evaluation")]
        ordering = ("-created",)
        indexes = [
            *ComponentJob.Meta.indexes,
            models.Index(fields=["created"]),
            models.Index(fields=["submission", "published", "status", "rank"]),
        ]

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.published = self.submission.phase.auto_publish_new_results

        super().save(*args, **kwargs)

        self.assign_permissions()

        on_commit(
            calculate_ranks.signature(
                kwargs={"phase_pk": self.submission.phase.pk}
            ).apply_async
        )

    @property
    def title(self):
        return f"#{self.rank} {self.submission.creator.username}"

    def assign_permissions(self):
        admins_group = self.submission.phase.challenge.admins_group
        assign_perm("view_evaluation", admins_group, self)
        assign_perm("change_evaluation", admins_group, self)

        if self.submission.phase.external_evaluation:
            external_evaluators = (
                self.submission.phase.challenge.external_evaluators_group
            )
            assign_perm("view_evaluation", external_evaluators, self)
            assign_perm("claim_evaluation", external_evaluators, self)

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
        return self.submission.phase.evaluation_outputs

    @property
    def additional_outputs(self):
        return self.outputs.exclude(interface__slug="metrics-json-file")

    @cached_property
    def successful_jobs_per_interface(self):
        algorithm_interfaces = (
            self.submission.phase.algorithm_interfaces.prefetch_related(
                "inputs"
            )
        )

        successful_jobs_per_interface = get_valid_jobs_for_interfaces_and_archive_items(
            subset_by_status=[Job.SUCCESS],
            algorithm_image=self.submission.algorithm_image,
            algorithm_model=self.submission.algorithm_model,
            algorithm_interfaces=algorithm_interfaces,
            valid_archive_items_per_interface=self.submission.phase.valid_archive_items_per_interface,
        )

        return successful_jobs_per_interface

    @cached_property
    def successful_job_count_per_interface(self):
        return {
            interface: len(successful_jobs)
            for interface, successful_jobs in self.successful_jobs_per_interface.items()
        }

    @cached_property
    def total_successful_jobs(self):
        return sum(self.successful_job_count_per_interface.values())

    @cached_property
    def successful_jobs(self):
        return Job.objects.filter(
            pk__in=[
                j.pk
                for sublist in self.successful_jobs_per_interface.values()
                for j in sublist
            ]
        )

    @cached_property
    def inputs_complete(self):
        if not self.additional_inputs_complete:
            return False

        if self.submission.algorithm_image:
            return (
                self.total_successful_jobs
                == self.submission.phase.jobs_to_schedule_per_submission
            )
        elif self.submission.predictions_file:
            return True
        else:
            return False

    @property
    def additional_inputs(self):
        # additional inputs as currently defined on the phase
        phase_input_slugs = (
            self.submission.phase.additional_evaluation_inputs.values_list(
                "slug", flat=True
            )
        )
        return self.inputs.filter(
            interface__slug__in=phase_input_slugs
        ).select_related("interface", "image")

    @cached_property
    def additional_inputs_complete(self):
        return (
            self.additional_inputs.count()
            == self.submission.phase.additional_evaluation_inputs.count()
        )

    @property
    def is_editable(self):
        # staying with display set and archive item terminology here
        # since this property is checked in create_civ()
        if self.status == self.VALIDATING_INPUTS:
            return True
        else:
            return False

    def add_civ(self, *, civ):
        super().add_civ(civ=civ)
        return self.inputs.add(civ)

    def remove_civ(self, *, civ):
        super().remove_civ(civ=civ)
        return self.inputs.remove(civ)

    def get_civ_for_interface(self, interface):
        return self.inputs.get(interface=interface)

    def validate_civ_data_objects_and_execute_linked_task(
        self, *, civ_data_objects, user, linked_task=None
    ):
        from grandchallenge.evaluation.tasks import (
            check_prerequisites_for_evaluation_execution,
        )

        linked_task = check_prerequisites_for_evaluation_execution.signature(
            kwargs={
                "evaluation_pk": self.pk,
            },
            immutable=True,
        )
        return super().validate_civ_data_objects_and_execute_linked_task(
            civ_data_objects=civ_data_objects,
            user=user,
            linked_task=linked_task,
        )

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

        if self.status in [self.FAILURE, self.SUCCESS, self.CANCELLED]:
            if self.status == self.CANCELLED:
                message = "was cancelled"
            else:
                message = self.get_status_display().lower()
            Notification.send(
                kind=NotificationTypeChoices.EVALUATION_STATUS,
                actor=self.submission.creator,
                message=message,
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

    @property
    def status_url(self) -> str:
        return reverse(
            "evaluation:status-detail",
            kwargs={
                "pk": self.pk,
                "challenge_short_name": self.submission.phase.challenge.short_name,
            },
        )

    def create_utilization(self):
        EvaluationUtilization.objects.create(evaluation=self)

    @property
    def utilization(self):
        return self.evaluation_utilization


class EvaluationUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Evaluation, on_delete=models.CASCADE)


class EvaluationGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset(
        {"change_evaluation", "view_evaluation", "claim_evaluation"}
    )

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

    class Meta:
        unique_together = (("phase", "combined_leaderboard"),)


class OptionalHangingProtocolPhase(models.Model):
    # Through table for optional hanging protocols
    # https://docs.djangoproject.com/en/4.2/topics/db/models/#intermediary-manytomany
    phase = models.ForeignKey(Phase, on_delete=models.CASCADE)
    hanging_protocol = models.ForeignKey(
        "hanging_protocols.HangingProtocol", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (("phase", "hanging_protocol"),)
