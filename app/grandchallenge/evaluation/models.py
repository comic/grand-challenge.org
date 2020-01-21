from pathlib import Path

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import BooleanField
from django.utils.text import get_valid_filename

from grandchallenge.challenges.models import Challenge
from grandchallenge.container_exec.backends.docker import Executor, put_file
from grandchallenge.container_exec.models import (
    ContainerExecJobModel,
    ContainerImageModel,
)
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.storage import protected_s3_storage, public_s3_storage
from grandchallenge.core.validators import (
    ExtensionValidator,
    JSONSchemaValidator,
    MimeTypeValidator,
    get_file_mimetype,
)
from grandchallenge.evaluation.emails import send_failed_job_email
from grandchallenge.subdomains.utils import reverse

# Example Schema
"""
[
  {
    "title": "Mean dice ± std",
    "path": "aggregates.dice.mean",
    "error_path": "aggregates.dice.std"
  },
  {
    "title": "Mean Hausdorff",
    "path": "aggregates.hausdorff.mean"
  }
]
"""
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


class Config(UUIDModel):
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
    PUBLICATION_LINK_CHOICES = SUPPLEMENTARY_FILE_CHOICES = (
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

    challenge = models.OneToOneField(
        Challenge,
        on_delete=models.CASCADE,
        related_name="evaluation_config",
        editable=False,
    )
    use_teams = models.BooleanField(
        default=False,
        help_text=(
            "If true, users are able to form teams together to participate in "
            "challenges."
        ),
    )
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
    extra_results_columns = JSONField(
        default=list,
        blank=True,
        help_text=(
            "A JSON object that contains the extra columns from metrics.json "
            "that will be displayed on the results page. "
        ),
        validators=[JSONSchemaValidator(schema=EXTRA_RESULT_COLUMNS_SCHEMA)],
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
    publication_url_choice = models.CharField(
        max_length=3,
        choices=PUBLICATION_LINK_CHOICES,
        default=OFF,
        help_text=(
            "Show a publication url field on the submission page so that "
            "users can submit a link to a publication that corresponds to "
            "their submission. Off turns this feature off, Optional means "
            "that including the url is optional for the user, Required means "
            "that the user must provide an url."
        ),
    )
    show_publication_url = models.BooleanField(
        default=False,
        help_text=("Show a link to the publication on the results page"),
    )

    daily_submission_limit = models.PositiveIntegerField(
        default=10,
        help_text=(
            "The limit on the number of times that a user can make a "
            "submission in a 24 hour period."
        ),
    )
    submission_page_html = models.TextField(
        help_text=(
            "HTML to include on the submission page for this challenge."
        ),
        blank=True,
    )
    auto_publish_new_results = BooleanField(
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
    submission_join_key = models.CharField(
        blank=True,
        default="",
        max_length=32,
        help_text=(
            "If predictions are submitted as csv files, which column should "
            "be used to join the data? eg. case_id"
        ),
    )

    def get_absolute_url(self):
        return reverse(
            "pages:home",
            kwargs={"challenge_short_name": self.challenge.short_name},
        )


def method_image_path(instance, filename):
    """Deprecated: only used in a migration."""
    return (
        f"{settings.EVALUATION_FILES_SUBDIRECTORY}/"
        f"{instance.challenge.pk}/"
        f"methods/"
        f"{instance.pk}/"
        f"{filename}"
    )


class Method(UUIDModel, ContainerImageModel):
    """Store the methods for performing an evaluation."""

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)

    def get_absolute_url(self):
        return reverse(
            "evaluation:method-detail",
            kwargs={
                "pk": self.pk,
                "challenge_short_name": self.challenge.short_name,
            },
        )


def submission_file_path(instance, filename):
    # Must match the protected serving url
    return (
        f"{settings.EVALUATION_FILES_SUBDIRECTORY}/"
        f"{instance.challenge.pk}/"
        f"submissions/"
        f"{instance.creator.pk}/"
        f"{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


def submission_supplementary_file_path(instance, filename):
    return (
        f"evaluation-supplementary/"
        f"{instance.challenge.pk}/"
        f"{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


class Submission(UUIDModel):
    """Store files for evaluation."""

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    file = models.FileField(
        upload_to=submission_file_path,
        validators=[
            MimeTypeValidator(allowed_types=("application/zip", "text/plain")),
            ExtensionValidator(allowed_extensions=(".zip", ".csv")),
        ],
        storage=protected_s3_storage,
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
    publication_url = models.URLField(
        blank=True,
        help_text=(
            "A URL for the publication associated with this submission."
        ),
    )

    def get_absolute_url(self):
        return reverse(
            "evaluation:submission-detail",
            kwargs={
                "pk": self.pk,
                "challenge_short_name": self.challenge.short_name,
            },
        )


class SubmissionEvaluator(Executor):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, results_file=Path("/output/metrics.json"), **kwargs
        )

    def _copy_input_files(self, writer):
        for file in self._input_files:
            dest_file = "/tmp/submission-src"
            put_file(container=writer, src=file, dest=dest_file)

            with file.open("rb") as f:
                mimetype = get_file_mimetype(f)

            if mimetype.lower() == "application/zip":
                # Unzip the file in the container rather than in the python
                # process. With resource limits this should provide some
                # protection against zip bombs etc.
                writer.exec_run(
                    f"unzip {dest_file} -d /input/ -x '__MACOSX/*'"
                )

                # Remove a duplicated directory
                input_files = (
                    writer.exec_run(f"ls -1 /input/")
                    .output.decode()
                    .splitlines()
                )

                if (
                    len(input_files) == 1
                    and not writer.exec_run(
                        f"ls -d /input/{input_files[0]}/"
                    ).exit_code
                ):
                    writer.exec_run(
                        f'/bin/sh -c "mv /input/{input_files[0]}/* /input/ '
                        f'&& rm -r /input/{input_files[0]}/"'
                    )

            else:
                # Not a zip file, so must be a csv
                writer.exec_run(f"mv {dest_file} /input/submission.csv")


class Result(UUIDModel):
    """Store individual results for a challenge."""

    job = models.OneToOneField("Job", null=True, on_delete=models.CASCADE)
    metrics = JSONField(default=dict)
    published = models.BooleanField(default=True)
    rank = models.PositiveIntegerField(
        default=0,
        help_text=(
            "The position of this result on the leaderboard. If the value is "
            "zero, then the result is unranked."
        ),
    )
    rank_score = models.FloatField(default=0.0)
    rank_per_metric = JSONField(default=dict)

    def save(self, *args, **kwargs):
        # Note: cannot use `self.pk is None` with a custom pk
        if self._state.adding:
            self.published = (
                self.job.submission.challenge.evaluation_config.auto_publish_new_results
            )

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "evaluation:result-detail",
            kwargs={
                "pk": self.pk,
                "challenge_short_name": self.job.submission.challenge.short_name,
            },
        )


class Job(UUIDModel, ContainerExecJobModel):
    """Stores information about a job for a given submission."""

    submission = models.ForeignKey("Submission", on_delete=models.CASCADE)
    method = models.ForeignKey("Method", on_delete=models.CASCADE)

    @property
    def container(self):
        return self.method

    @property
    def input_files(self):
        return [self.submission.file]

    @property
    def executor_cls(self):
        return SubmissionEvaluator

    def create_result(self, *, result):
        Result.objects.create(job=self, metrics=result)

    def clean(self):
        if self.submission.challenge != self.method.challenge:
            raise ValidationError(
                "The submission and method challenges should"
                "be the same. You are trying to evaluate a"
                f"submission for {self.submission.challenge}"
                f"with a method for {self.method.challenge}"
            )

        super().clean()

    def update_status(self, *args, **kwargs):
        res = super().update_status(*args, **kwargs)

        if self.status == self.FAILURE:
            send_failed_job_email(self)

        return res

    def get_absolute_url(self):
        return reverse(
            "evaluation:job-detail",
            kwargs={
                "pk": self.pk,
                "challenge_short_name": self.submission.challenge.short_name,
            },
        )


def result_screenshot_path(instance, filename):
    # Used in a migration so cannot delete
    return (
        f"evaluation/"
        f"{instance.challenge.pk}/"
        f"screenshots/"
        f"{instance.result.pk}/"
        f"{instance.pk}/"
        f"{filename}"
    )
