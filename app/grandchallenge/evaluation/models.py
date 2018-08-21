from pathlib import Path

from ckeditor.fields import RichTextField
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import BooleanField

from grandchallenge.challenges.models import Challenge
from grandchallenge.container_exec.backends.docker import Executor, put_file
from grandchallenge.container_exec.models import (
    ContainerExecJobModel,
    ContainerImageModel,
)
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.core.validators import (
    MimeTypeValidator,
    ExtensionValidator,
    get_file_mimetype,
)
from grandchallenge.evaluation.emails import send_failed_job_email


class Config(UUIDModel):
    # This must match the syntax used in jquery datatables
    # https://datatables.net/reference/option/order
    ASCENDING = "asc"
    DESCENDING = "desc"
    EVALUATION_SCORE_SORT_CHOICES = (
        (ASCENDING, "Ascending"),
        (DESCENDING, "Descending"),
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
    score_jsonpath = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "The jsonpath of the field in metrics.json that will be used "
            "for the overall scores on the results page. See "
            "http://goessner.net/articles/JsonPath/ for syntax. For example:"
            "\n\ndice.mean"
        ),
    )
    score_title = models.CharField(
        max_length=32,
        blank=False,
        default="Score",
        help_text=(
            "The name that will be displayed for the scores column, for "
            "instance:\n\nScore (log-loss)"
        ),
    )
    score_default_sort = models.CharField(
        max_length=4,
        choices=EVALUATION_SCORE_SORT_CHOICES,
        default=DESCENDING,
        help_text=(
            "The default sorting to use for the scores on the results " "page."
        ),
    )
    extra_results_columns = JSONField(
        default=dict,
        blank=True,
        help_text=(
            "A JSON object that contains the extra columns from metrics.json "
            "that will be displayed on the results page. "
            "Where the KEYS contain the titles of the columns, "
            "and the VALUES contain the JsonPath to the corresponding metric "
            "in metrics.json. "
            "For example:\n\n"
            '{"Accuracy": "aggregates.acc","Dice": "dice.mean"}'
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
    allow_supplementary_file = models.BooleanField(
        default=False,
        help_text=(
            "Show a supplementary file field on the submissions page so that "
            "users can upload an additional file along with their predictions "
            "file as part of their submission (eg, include a pdf description "
            "of their method)."
        ),
    )
    require_supplementary_file = models.BooleanField(
        default=False,
        help_text=(
            "Force users to upload a supplementary file with their "
            "predictions file."
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
    daily_submission_limit = models.PositiveIntegerField(
        default=10,
        help_text=(
            "The limit on the number of times that a user can make a "
            "submission in a 24 hour period."
        ),
    )
    submission_page_html = RichTextField(
        help_text=(
            "HTML to include on the submission page for this challenge."
        ),
        blank=True,
    )
    new_results_are_public = BooleanField(
        default=True,
        help_text=(
            "If true, new results are automatically made public. If false, "
            "the challenge administrator must manually publish each new "
            "result."
        ),
    )

    def get_absolute_url(self):
        return reverse(
            "challenge-homepage",
            kwargs={"challenge_short_name": self.challenge.short_name},
        )


def method_image_path(instance, filename):
    """ Deprecated: only used in a migration """
    return (
        f"evaluation/"
        f"{instance.challenge.pk}/"
        f"methods/"
        f"{instance.pk}/"
        f"{filename}"
    )


class Method(UUIDModel, ContainerImageModel):
    """
    Stores the methods for performing an evaluation
    """

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
    return (
        f"evaluation/"
        f"{instance.challenge.pk}/"
        f"submissions/"
        f"{instance.creator.pk}/"
        f"{instance.pk}/"
        f"{filename}"
    )


def submission_supplementary_file_path(instance, filename):
    return (
        f"evaluation-supplementary/"
        f"{instance.challenge.pk}/"
        f"{instance.creator.pk}/"
        f"{instance.pk}/"
        f"{filename}"
    )


class Submission(UUIDModel):
    """
    Stores files for evaluation
    """

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    # Limitation for now: only accept zip files as these are expanded in
    # evaluation.tasks.Evaluation. We could extend this first to csv file
    # submission with some validation
    file = models.FileField(
        upload_to=submission_file_path,
        validators=[
            MimeTypeValidator(allowed_types=("application/zip", "text/plain")),
            ExtensionValidator(allowed_extensions=(".zip", ".csv")),
        ],
    )
    supplementary_file = models.FileField(
        upload_to=submission_supplementary_file_path,
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
                writer.exec_run(f"unzip {dest_file} -d /input/")
            else:
                # Not a zip file, so must be a csv
                writer.exec_run(f"mv {dest_file} /input/submission.csv")


class Result(UUIDModel):
    """
    Stores individual results for a challenges
    """

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    job = models.OneToOneField("Job", null=True, on_delete=models.CASCADE)
    metrics = JSONField(default=dict)
    public = models.BooleanField(default=True)
    rank = models.PositiveIntegerField(
        default=0,
        help_text=(
            "The position of this result on the leaderboard. If the value is "
            "zero, then the result is unranked."
        ),
    )
    # Cache the url as this is slow on the results list page
    absolute_url = models.TextField(blank=True, editable=False)

    def save(self, *args, **kwargs):
        # Note: cannot use `self.pk is None` with a custom pk
        if self._state.adding:
            self.public = (
                self.challenge.evaluation_config.new_results_are_public
            )

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "evaluation:result-detail",
            kwargs={
                "pk": self.pk,
                "challenge_short_name": self.challenge.short_name,
            },
        )


class Job(UUIDModel, ContainerExecJobModel):
    """
    Stores information about a job for a given upload
    """

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
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
        Result.objects.create(
            job=self, challenge=self.challenge, metrics=result
        )

    def clean(self):
        if self.submission.challenge != self.method.challenge:
            raise ValidationError(
                "The submission and method challenges should"
                "be the same. You are trying to evaluate a"
                f"submission for {self.submission.challenge}"
                f"with a method for {self.method.challenge}"
            )

        super().clean()

    def save(self, *args, **kwargs):
        self.challenge = self.submission.challenge
        super().save(*args, **kwargs)

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
                "challenge_short_name": self.challenge.short_name,
            },
        )


def result_screenshot_path(instance, filename):
    return (
        f"evaluation/"
        f"{instance.challenge.pk}/"
        f"screenshots/"
        f"{instance.result.pk}/"
        f"{instance.pk}/"
        f"{filename}"
    )


class ResultScreenshot(UUIDModel):
    """
    Stores a screenshot that is generated during an evaluation
    """

    result = models.ForeignKey("Result", on_delete=models.CASCADE)
    image = models.ImageField(upload_to=result_screenshot_path)
