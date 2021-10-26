import logging
from datetime import timedelta
from urllib.parse import parse_qs, urljoin, urlparse

from actstream.actions import follow, is_following
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.db.transaction import on_commit
from django.utils import timezone
from django.utils.text import get_valid_filename
from django_extensions.db.fields import AutoSlugField
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.archives.models import Archive
from grandchallenge.challenges.models import Challenge
from grandchallenge.components.models import (
    ComponentImage,
    ComponentInterface,
    ComponentJob,
)
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.storage import protected_s3_storage, public_s3_storage
from grandchallenge.core.validators import (
    ExtensionValidator,
    JSONValidator,
    MimeTypeValidator,
)
from grandchallenge.evaluation.tasks import calculate_ranks, create_evaluation
from grandchallenge.notifications.models import Notification, NotificationType
from grandchallenge.subdomains.utils import reverse
from grandchallenge.uploads.models import UserUpload

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
        },
    },
}

OBSERVABLE_URL_VALIDATOR = RegexValidator(
    r"^https\:\/\/observablehq\.com\/embed\/\@[^\/]+\/[^\?\.]+\?cell\=.*$",
    "URL must be of the form https://observablehq.com/embed/@user/notebook?cell=*",
)


class Phase(UUIDModel):
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

    class SubmissionKind(models.IntegerChoices):
        CSV = 1, "CSV"
        ZIP = 2, "ZIP"
        ALGORITHM = 3, "Algorithm"

    challenge = models.ForeignKey(
        Challenge, on_delete=models.PROTECT, editable=False,
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
        default="Challenge",
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
            "that will be displayed on the results page. "
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
        default=SubmissionKind.CSV,
        choices=SubmissionKind.choices,
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
    submission_limit = models.PositiveIntegerField(
        default=10,
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
    submissions_open = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "If set, participants will not be able to make submissions to "
            "this phase before this time."
        ),
    )
    submissions_close = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "If set, participants will not be able to make submissions to "
            "this phase after this time."
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

    evaluation_detail_observable_url = models.URLField(
        blank=True,
        validators=[OBSERVABLE_URL_VALIDATOR],
        max_length=2000,
        help_text=(
            "The URL of the embeddable observable notebook for viewing "
            "individual results. Must be of the form "
            "https://observablehq.com/embed/@user/notebook?cell=..."
        ),
    )
    evaluation_comparison_observable_url = models.URLField(
        blank=True,
        validators=[OBSERVABLE_URL_VALIDATOR],
        max_length=2000,
        help_text=(
            "The URL of the embeddable observable notebook for comparing"
            "results. Must be of the form "
            "https://observablehq.com/embed/@user/notebook?cell=..."
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

    class Meta:
        unique_together = (
            ("challenge", "title"),
            ("challenge", "slug"),
        )
        ordering = ("challenge", "submissions_open", "created")
        permissions = (
            ("create_phase_submission", "Create Phase Submission"),
            ("create_phase_workspace", "Create Phase Workspace"),
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

        on_commit(
            lambda: calculate_ranks.apply_async(kwargs={"phase_pk": self.pk})
        )

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
        assign_perm(
            "create_phase_submission", self.challenge.participants_group, self
        )

    def get_absolute_url(self):
        return reverse(
            "pages:home",
            kwargs={"challenge_short_name": self.challenge.short_name},
        )

    def get_observable_url(self, view_kind, url_kind):
        if view_kind == "detail":
            url = self.evaluation_detail_observable_url
        elif view_kind == "comparison":
            url = self.evaluation_comparison_observable_url
        else:
            raise ValueError("View or notebook not found")

        if not url:
            return "", []

        parsed_url = urlparse(url)
        cells = parse_qs(parsed_url.query)["cell"]
        url = f"{urljoin(url, parsed_url.path)}"

        if url_kind == "js":
            url = url.replace(
                "https://observablehq.com/embed/",
                "https://api.observablehq.com/",
            )
            url += ".js?v=3"
        elif url_kind == "edit":
            url = url.replace(
                "https://observablehq.com/embed/", "https://observablehq.com/"
            )
        else:
            raise ValueError("URL kind must be one of edit or js")

        return url, cells

    @property
    def observable_detail_edit_url(self):
        url, _ = self.get_observable_url(view_kind="detail", url_kind="edit")
        return url

    @property
    def observable_comparison_edit_url(self):
        url, _ = self.get_observable_url(
            view_kind="comparison", url_kind="edit"
        )
        return url

    @property
    def submission_limit_period_timedelta(self):
        return timedelta(days=self.submission_limit_period)

    def get_next_submission(self, *, user):
        """
        Determines the number of submissions left for the user,
        and when they can next submit.
        """
        now = timezone.now()

        filter_kwargs = {"creator": user}

        if self.submission_limit_period is not None:
            filter_kwargs.update(
                {"created__gte": now - self.submission_limit_period_timedelta}
            )

        evals_in_period = (
            self.submission_set.filter(**filter_kwargs)
            .exclude(evaluation__status=Evaluation.FAILURE)
            .distinct()
            .order_by("-created")
        )

        remaining_submissions = max(
            0, self.submission_limit - evals_in_period.count()
        )

        if remaining_submissions:
            next_sub_at = now
        elif (
            self.submission_limit == 0 or self.submission_limit_period is None
        ):
            # User is never going to be able to submit again
            next_sub_at = None
        else:
            next_sub_at = (
                evals_in_period[self.submission_limit - 1].created
                + self.submission_limit_period_timedelta
            )

        return {
            "remaining_submissions": remaining_submissions,
            "next_submission_at": next_sub_at,
        }

    def has_pending_evaluations(self, *, user):
        return (
            Evaluation.objects.filter(
                submission__phase=self, submission__creator=user,
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

    def get_absolute_url(self):
        return reverse(
            "evaluation:method-detail",
            kwargs={
                "pk": self.pk,
                "challenge_short_name": self.phase.challenge.short_name,
            },
        )


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
        AlgorithmImage, null=True, on_delete=models.SET_NULL
    )
    user_upload = models.ForeignKey(
        UserUpload, blank=True, null=True, on_delete=models.SET_NULL,
    )
    predictions_file = models.FileField(
        upload_to=submission_file_path,
        validators=[
            MimeTypeValidator(allowed_types=("application/zip", "text/plain")),
            ExtensionValidator(allowed_extensions=(".zip", ".csv")),
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
        blank=True, help_text="A URL associated with this submission.",
    )

    class Meta:
        unique_together = (("phase", "predictions_file", "algorithm_image"),)

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
                kwargs={"submission_pk": self.pk}, immutable=True,
            )
            on_commit(e.apply_async)

    def assign_permissions(self):
        assign_perm("view_submission", self.phase.challenge.admins_group, self)
        assign_perm("view_submission", self.creator, self)

    @property
    def latest_ready_method(self):
        return (
            Method.objects.filter(phase=self.phase, ready=True)
            .order_by("-created")
            .first()
        )

    def get_absolute_url(self):
        return reverse(
            "evaluation:submission-detail",
            kwargs={
                "pk": self.pk,
                "challenge_short_name": self.phase.challenge.short_name,
            },
        )


class Evaluation(UUIDModel, ComponentJob):
    """Stores information about a evaluation for a given submission."""

    submission = models.ForeignKey("Submission", on_delete=models.PROTECT)
    method = models.ForeignKey("Method", on_delete=models.PROTECT)

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

        if self.submission.phase.challenge.hidden:
            viewer_group = self.submission.phase.challenge.participants_group
            non_viewer_group = Group.objects.get(
                name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
            )
        else:
            viewer_group = Group.objects.get(
                name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
            )
            non_viewer_group = (
                self.submission.phase.challenge.participants_group
            )

        if self.published:
            assign_perm("view_evaluation", viewer_group, self)
        else:
            remove_perm("view_evaluation", viewer_group, self)

        remove_perm("view_evaluation", non_viewer_group, self)

    @property
    def container(self):
        return self.method

    @property
    def output_interfaces(self):
        return self.submission.phase.outputs

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
                type=NotificationType.NotificationTypeChoices.EVALUATION_STATUS,
                actor=self.submission.creator,
                message="failed",
                action_object=self,
                target=self.submission.phase,
            )

        if self.status == self.SUCCESS:
            Notification.send(
                type=NotificationType.NotificationTypeChoices.EVALUATION_STATUS,
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
