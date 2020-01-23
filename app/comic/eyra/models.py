import logging
import os
import uuid

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.postgres.fields import JSONField

# from comic.eyra_algorithms.validators import IdExistsInDockerRegistryValidator

logger = logging.getLogger(__name__)


class UUIDModel(models.Model):
    """
    Abstract class that consists of a UUID primary key, created and modified times
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID (primary key)"
    )
    created = models.DateTimeField(
        auto_now_add=True,
        help_text="Moment of creation"
    )
    modified = models.DateTimeField(
        auto_now=True,
        help_text="Moment of last modification"
    )

    class Meta:
        abstract = True


def get_banner_image_filename(obj, filename=None):
    extension = os.path.splitext(filename)[1]
    return 'benchmarks/'+str(obj.id)+'/banner_image'+extension


def get_card_image_filename(obj, filename=None):
    extension = os.path.splitext(filename)[1]
    return 'benchmarks/'+str(obj.id)+'/card_image'+extension


class Benchmark(UUIDModel):
    """
    A `Benchmark` defines a specific challenge.

    To be a valid `Benchmark`, for which submissions can be created which can be evaluated, a couple of things need
    to be specified:

    `data_set` field:
        Sets the :class:`~comic.eyra_data.models.DataSet` to be used in this benchmark. Determines which files are used
        as test data and ground truth in the evaluation pipeline.

    `evaluation_image` field:
        The evaluator field sets which docker image is
        used to evaluate the output of a user :class:`Submission`.
    """
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        help_text="Creator of the benchmark",
    )
    short_description = models.TextField(
        default="",
        help_text="Short description in markdown",
    )
    description = models.TextField(
        default="",
        help_text="Description in markdown",
    )
    data_description = models.TextField(
        default="",
        help_text="Description of the data used in this benchmark in markdown",
    )
    truth_description = models.TextField(
        default="",
        help_text="Description of the truth data in markdown",
    )
    metrics_description = models.TextField(
        default="",
        help_text="Description of the metrics in markdown",
    )
    name = models.CharField(
        max_length=255,
        blank=False,
        help_text="The name of the benchmark",
        unique=True,
    )
    banner_image = models.ImageField(
        blank=True,
        null=True,
        upload_to=get_banner_image_filename,
        help_text="Banner image (wide image that shows in header of benchmark details page)",
    )
    card_image = models.ImageField(
        blank=True,
        null=True,
        upload_to=get_card_image_filename,
        help_text="Image to show in small card of this benchmark",
    )
    evaluation_image = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Docker image to use for evaluation."
    )
    data_set = models.ForeignKey(
        'DataSet',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='benchmarks',
        help_text="Data set used in this benchmark",
    )
    admin_group = models.OneToOneField(
        Group,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="benchmark",
        help_text="Admin group for this benchmark"
    )

    def save(self, *args, **kwargs):
        from comic.eyra.utils import set_benchmark_admin_group, set_benchmark_default_permissions
        set_benchmark_admin_group(self)
        self.full_clean()
        super().save(*args, **kwargs)
        set_benchmark_default_permissions(self)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "benchmark"
        verbose_name_plural = "benchmarks"


class Submission(UUIDModel):
    """
    A `Submission` is an algorithm (as a docker image) tested for a
    :class:`Benchmark`. Whenever a `Submission` is created, two :class:`Jobs <comic.eyra_algorithms.models.Job>`
    are created: the algorithm_job (which runs first) and the evaluation_job (which runs second, using the output
    of the first :class:`~comic.eyra_algorithms.models.Job`.

    When the evaluation :class:`~comic.eyra_algorithms.models.Job` succeeds, the field `metrics` in its JSON output
    will be copied to this models `metrics`.
    """
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="submissions",
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=255, unique=True, null=True, blank=True)
    benchmark = models.ForeignKey(Benchmark, on_delete=models.CASCADE)
    algorithm_job = models.ForeignKey('Job', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    evaluation_job = models.ForeignKey('Job', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    metrics = JSONField(null=True, blank=True)
    is_private = models.BooleanField(
        default=False,
        help_text=(
            "Submission for private leaderboard"
        )
    )
    visualization_url = models.URLField(
        null=True,
        blank=True,
        help_text=(
            "Visualization URL"
        ),
    )
    image = models.CharField(
        max_length=64,
        unique=True,
        # validators=[IdExistsInDockerRegistryValidator],
        help_text="Docker image (e.g. eyra/frb-eval:3)",
    )
    command = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="If specified, overrides default command as defined in Dockerfile",
    )
    algorithm = models.ForeignKey(
        'Algorithm',
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name='algorithm',
        help_text='Implemented algorithm',
    )
    version = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Version",
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        if self.is_private:
            if not self.benchmark.data_set.private_test_data_file:
                raise ValidationError('Cannot create private submission, because the Benchmarks dataset has no private_test_data_file')
            if not self.benchmark.data_set.private_ground_truth_data_file:
                raise ValidationError('Cannot create private submission, because the Benchmarks dataset has no private_ground_truth_data_file')
        else:
            if not self.benchmark.data_set.public_test_data_file:
                raise ValidationError('Cannot create public submission, because the Benchmarks dataset has no public_test_data_file')
            if not self.benchmark.data_set.public_ground_truth_data_file:
                raise ValidationError('Cannot create public submission, because the Benchmarks dataset has no public_ground_truth_data_file')


class Algorithm(UUIDModel):
    """
    Algorithms group submissions.
    """
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="algorithms",
        help_text="Created by user",
    )
    name = models.CharField(
        max_length=255,
        unique=True,
        null=False,
        blank=False,
        help_text="Name of algorithm",
    )
    description = models.TextField(
        default="",
        blank=True,
        help_text="Description of this solution in markdown",
    )
    admin_group = models.OneToOneField(
        Group,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="algorithm",
        help_text="The admin group associated with this algorithm",
    )
    tags = ArrayField(
        models.CharField(max_length=30, blank=False, null=False),
        blank=True,
        help_text="Tags associated with this algorithm",
    )
    source_code_link = models.URLField(
        null=True,
        blank=True,
        help_text="Link to the source code"
    )
    paper_link = models.URLField(
        null=True,
        blank=True,
        help_text="Link to a paper or blog post"
    )

    def save(self, *args, **kwargs):
        from comic.eyra.utils import set_algorithm_admin_group, set_algorithm_default_permissions
        set_algorithm_admin_group(self)
        super().save(*args, **kwargs)
        set_algorithm_default_permissions(self)

    def __str__(self):
        return self.name


class Job(UUIDModel):
    """
    A `Job` represents a run of an :class:`Submission`. It keeps track of the status, start & stop times,
    log (combined `stdout` and `stderr`), and output.

    Status codes::

        PENDING   = 0   # (Job is waiting to start)
        STARTED   = 1   # (Job is running)
        RETRY     = 2   # (Not used)
        FAILURE   = 3   # (Job finished unsuccessfully (exit code not 0))
        SUCCESS   = 4   # (Job finished with exit code 0
        CANCELLED = 5   # (Not used)
    """
    PENDING = 0
    STARTED = 1
    RETRY = 2
    FAILURE = 3
    SUCCESS = 4
    CANCELLED = 5

    STATUS_CHOICES = (
        (PENDING, "Queued"),
        (STARTED, "Started"),
        (RETRY, "Re-Queued"),
        (FAILURE, "Failed"),
        (SUCCESS, "Succeeded"),
        (CANCELLED, "Cancelled"),
    )
    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES,
        default=PENDING,
        help_text="Status of the job",
    )
    started = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Moment job was started",
    )
    stopped = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Moment job completed (success or fail)",
    )
    log = models.TextField(
        blank=True,
        null=True,
        help_text="Combined stderr/stdout of the job",
    )
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        help_text="Submission being run",
        # Nullable because this job could be an evaluation job as well
        null=True,
        blank=True,
    )
    output = models.ForeignKey(
        'DataFile',
        on_delete=models.CASCADE,
        related_name='output_of_job',
        null=False,
        blank=False,
        help_text="Output of the job",
    )

    def delete(self, using=None, keep_parents=False):
        if self.output:
            self.output.delete()
        super().delete(using, keep_parents)

    def input_name_data_file_pk_map(self):
        return {job_input.name: job_input.data_file.pk for job_input in self.inputs.all()}


class JobInput(UUIDModel):
    """
    Input of a :class:`Job`, a link between the :class:`Input` of an :class:`Submission` and a specific
    :class:`~comic.eyra_data.models.DataFile`.
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        null=False,
        blank=False,
        help_text="Name of algorithm",
    )
    data_file = models.ForeignKey(
        'DataFile',
        on_delete=models.CASCADE,
        related_name='job_inputs',
        help_text="Input DataFile",
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='inputs',
        help_text="Job that this input is for",
    )


def get_data_file_name(obj, filename=None):
    return 'data_files/'+str(obj.id)


class DataFile(UUIDModel):
    """
    Represents a file
    """
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="data_files",
        help_text="Creator of this DataFile",
    )

    name = models.CharField(
        max_length=50,
        null=False,
        blank=False,
        help_text="Name of this file",
    )
    file = models.FileField(
        blank=True,
        null=True,
        upload_to=get_data_file_name,
        help_text="This files contents (the bits)",
    )
    sha = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        help_text="Reserved for SHA checksum (currently not used)"
    )

    short_description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Short description of this file in plain text.",
    )
    long_description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Description of this file in markdown.",
    )
    size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="The size of this file in bytes",
    )

    def get_download_url(self):
        storage = self.file.storage
        if storage.bucket:  # s3 storage
            return storage.bucket.meta.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': storage.bucket.name,
                    'Key': storage._encode_name(self.file.name),
                    'ResponseContentDisposition': f'attachment; filename="{self.name}"'
                })
        return self.file.url

    def __str__(self):
        return self.name


class DataSet(UUIDModel):
    """
    DataSets are used in :class:`Benchmarks <comic.eyra_benchmarks.models.Benchmark>`.
    """
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="data_sets",
        help_text="Creator of this DataSet",
    )
    version = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="The Dataset version",
    )
    name = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        help_text="The name of this dataset",
    )
    short_description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Short description of this data set in plaintext.",
    )
    long_description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Long description of this data set in markdown.",
    )
    card_image_url = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        default="https://www.staging.eyrabenchmark.net/static/media/logo.3fc4ddae.png",
        help_text="Image used in the DataSet card component",
    )
    card_image_alttext = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="alt attribute for image in DataSet card component",
    )
    banner_image_url = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        default="https://www.staging.eyrabenchmark.net/static/media/logo.3fc4ddae.png",
        help_text="(wide) image used as a banner in DataSet detail page",
    )
    banner_image_alttext = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="alt attribute for image in DataSet details header",
    )
    related_datasets = models.ManyToManyField(
        "DataSet",
        blank=True,
        related_name='related_data_sets',
        help_text="Other DataSets related to this one",
    )
    public_test_data_file = models.ForeignKey(
        DataFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="DataFile used as 'test_data' input in public submission container",
    )
    public_ground_truth_data_file = models.ForeignKey(
        DataFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="DataFile used as 'ground_truth' input in public evaluation container",
    )
    public_test_data_description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Description of the test data.",
    )
    public_test_data_sampling_method = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Sampling method of the test data.",
    )

    private_test_data_file = models.ForeignKey(
        DataFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="DataFile used as 'test_data' input in private submission container",
    )
    private_ground_truth_data_file = models.ForeignKey(
        DataFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="DataFile used as 'ground_truth' input in private evaluation container",
    )
    private_test_data_description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Description of the test data.",
    )
    private_test_data_sampling_method = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Sampling method of the test data.",
    )

    participant_data_files = models.ManyToManyField(
        DataFile,
        related_name='data_sets',
        blank=True,
        help_text="Other DataFiles downloadable by a participant.",
    )
    participant_data_description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Description of the data.",
    )
    participant_data_sampling_method = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Sampling method of the data.",
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
