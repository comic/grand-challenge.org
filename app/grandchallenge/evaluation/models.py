import logging
from json import dumps
from urllib.parse import parse_qs, urljoin, urlparse

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import get_valid_filename
from django_extensions.db.fields import AutoSlugField
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.algorithms.tasks import (
    create_algorithm_jobs_for_evaluation,
)
from grandchallenge.archives.models import Archive
from grandchallenge.challenges.models import Challenge
from grandchallenge.components.backends.docker import (
    Executor,
    put_file,
)
from grandchallenge.components.models import (
    ComponentImage,
    ComponentInterface,
    ComponentInterfaceValue,
    ComponentJob,
)
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.storage import protected_s3_storage, public_s3_storage
from grandchallenge.core.validators import (
    ExtensionValidator,
    JSONSchemaValidator,
    MimeTypeValidator,
    get_file_mimetype,
)
from grandchallenge.evaluation.emails import (
    send_failed_evaluation_email,
    send_missing_method_email,
    send_successful_evaluation_email,
)
from grandchallenge.evaluation.tasks import calculate_ranks
from grandchallenge.subdomains.utils import reverse

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

    class SubmissionKind(models.IntegerChoices):
        CSV = 1, "CSV"
        ZIP = 2, "ZIP"
        ALGORITHM = 3, "Algorithm"

    challenge = models.ForeignKey(
        Challenge, on_delete=models.CASCADE, editable=False,
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

    class Meta:
        unique_together = (
            ("challenge", "title"),
            ("challenge", "slug"),
        )
        ordering = ("challenge", "submissions_open", "created")
        permissions = (("create_phase_submission", "Create Phase Submission"),)

    def __str__(self):
        return f"{self.title} Evaluation for {self.challenge.short_name}"

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.set_default_interfaces()
            self.assign_permissions()

        calculate_ranks.apply_async(kwargs={"phase_pk": self.pk})

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


class Method(UUIDModel, ComponentImage):
    """Store the methods for performing an evaluation."""

    phase = models.ForeignKey(Phase, on_delete=models.CASCADE, null=True)

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
    creators_ip = models.GenericIPAddressField(
        null=True, default=None, editable=False
    )
    creators_user_agent = models.TextField(
        blank=True, default="", editable=False
    )

    phase = models.ForeignKey(Phase, on_delete=models.CASCADE, null=True)
    algorithm_image = models.ForeignKey(
        AlgorithmImage, null=True, on_delete=models.SET_NULL
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
    publication_url = models.URLField(
        blank=True,
        help_text=(
            "A URL for the publication associated with this submission."
        ),
    )

    class Meta:
        unique_together = (("phase", "predictions_file", "algorithm_image"),)

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.create_evaluation()
            self.assign_permissions()

    def assign_permissions(self):
        assign_perm("view_submission", self.phase.challenge.admins_group, self)
        assign_perm("view_submission", self.creator, self)

    def create_evaluation(self):
        method = self.latest_ready_method

        if not method:
            send_missing_method_email(self)
            return

        evaluation = Evaluation.objects.create(submission=self, method=method)

        if self.algorithm_image:
            create_algorithm_jobs_for_evaluation.apply_async(
                kwargs={"evaluation_pk": evaluation.pk}
            )
        else:
            mimetype = get_file_mimetype(self.predictions_file)

            if mimetype == "application/zip":
                interface = ComponentInterface.objects.get(
                    slug="predictions-zip-file"
                )
            elif mimetype == "text/plain":
                interface = ComponentInterface.objects.get(
                    slug="predictions-csv-file"
                )
            else:
                evaluation.update_status(
                    status=Evaluation.FAILURE,
                    stderr=f"{mimetype} files are not supported.",
                    error_message=f"{mimetype} files are not supported.",
                )
                return

            evaluation.inputs.set(
                [
                    ComponentInterfaceValue.objects.create(
                        interface=interface, file=self.predictions_file
                    )
                ]
            )
            evaluation.signature.apply_async()

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


class SubmissionEvaluator(Executor):
    def _copy_input_files(self, writer):
        for file in self._input_files:
            dest_file = "/tmp/submission-src"
            put_file(container=writer, src=file, dest=dest_file)

            if hasattr(file, "content_type"):
                mimetype = file.content_type
            else:
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
                    writer.exec_run("ls -1 /input/")
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

            elif mimetype.lower() == "application/json":
                writer.exec_run(f"mv {dest_file} /input/predictions.json")

            else:
                # Not a zip file, so must be a csv
                writer.exec_run(f"mv {dest_file} /input/submission.csv")


class Evaluation(UUIDModel, ComponentJob):
    """Stores information about a evaluation for a given submission."""

    submission = models.ForeignKey("Submission", on_delete=models.CASCADE)
    method = models.ForeignKey("Method", on_delete=models.CASCADE)

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

        calculate_ranks.apply_async(
            kwargs={"phase_pk": self.submission.phase.pk}
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
    def input_files(self):
        try:
            return [
                SimpleUploadedFile(
                    "predictions.json",
                    dumps(
                        self.inputs.get(
                            interface__title="Predictions JSON File"
                        ).value
                    ).encode("utf-8"),
                    content_type="application/json",
                )
            ]
        except ObjectDoesNotExist:
            return [inpt.file for inpt in self.inputs.all()]

    @property
    def output_interfaces(self):
        return self.submission.phase.outputs

    @property
    def executor_cls(self):
        return SubmissionEvaluator

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
            send_failed_evaluation_email(self)

        if self.status == self.SUCCESS:
            send_successful_evaluation_email(self)

        return res

    def get_absolute_url(self):
        return reverse(
            "evaluation:detail",
            kwargs={
                "pk": self.pk,
                "challenge_short_name": self.submission.phase.challenge.short_name,
            },
        )
