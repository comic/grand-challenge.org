import logging

from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models

from comic.core.models import UUIDModel
from comic.eyra_data.models import DataType, DataFile
from comic.eyra_algorithms.validators import IdExistsInDockerRegistryValidator

logger = logging.getLogger(__name__)


class Interface(UUIDModel):
    """
    An `Interface` is like a programming language interface: it defines input and output names &
    :class:`DataTypes <comic.eyra_data.models.DataType>`.
    There can be multiple inputs, but always a single output.

    For instance the representation of an 'evaluation' :class:`~comic.eyra_algorithms.models.Algorithm`
    looks like this::

        Inputs:
            - ground_truth: (type: CSV file)
            - implementation_output: (type: FRB Candidates)
        Output:
            - (type: OutputMetrics)

    Any evaluation container should follow the above structure, although the inputs can be of a different
    :class:`~comic.eyra_data.models.DataType`.

    Similarly, the interface for a user-submitted :class:`~comic.eyra_algorithms.models.Algorithm` might
    look like this::

        Inputs:
            - test_data: (type: CSV file)
        Output:
            - (type: FRB Candidates)

    The `Interface` thus defines which :class:`Implementation` 's can be plugged into one another.

    The above two examples together define the typical pipeline structure of a
    :class:`~comic.eyra_benchmarks.models.Benchmark`. I.e. the output of the second example becomes the
    `implementation_output` :class:`Input` of the first example.
    """

    name = models.CharField(
        max_length=64,
        unique=True,
        help_text="Name of the interface"
    )
    output_type = models.ForeignKey(
        DataType,
        on_delete=models.CASCADE,
        related_name='+',
        help_text="Output DataType"
    )

    def __str__(self):
        # example: FRB Evaluator: (ground_truth: CSV file, implementation_output: FRB Candidates -> OutputMetrics)
        input_str = ', '.join([f'{i.name}: {i.type}' for i in self.inputs.all()])
        return f'{self.name} ({input_str} -> {self.output_type.name})'


class Input(UUIDModel):
    """
    Combination of `name`, and :class:`type <comic.eyra_data.models.DataType>`.
    Represents a single `Input` of an :class:`~Implementation`.
    """
    name = models.CharField(
        max_length=64,
        help_text="Input name"
    )
    interface = models.ForeignKey(
        Interface,
        on_delete=models.CASCADE,
        related_name='inputs',
        help_text="Implementation"
    )
    type = models.ForeignKey(
        DataType,
        on_delete=models.CASCADE,
        related_name='+',
        help_text="Data type"
    )

    def __str__(self):
        return self.name


class Algorithm(UUIDModel):
    """
    An Algorithm has a single :class:`Interface` and represents a group (different versions) of
    :class:`Implementations <comic.eyra_algorithms.models.Implementation>`.
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
    interface = models.ForeignKey(
        Interface,
        on_delete=models.CASCADE,
        related_name='algorithms',
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

    def delete(self, *args, **kwargs):
        if self.admin_group:
            self.admin_group.delete()
        return super().delete(*args, **kwargs)

    def __str__(self):
        return self.name


class Implementation(UUIDModel):
    """
    An implementation belongs to a single :class:`Algorithm`. It is a concrete implementation that is supposed
    to generate output given a set of inputs according to an Algorithm's :class:`Interface`.

    The code to run this implementation should be a Docker image, specified by the `image` field. This is equal
    to a Docker tag, e.g. :code:`[repository]/[org]/[image]:[version]`.
    Also see `the docker documentation <https://docs.docker.com/engine/reference/commandline/tag/>`_.

    If the `repository` part is not present in the image field, it is by default assumed to refer to DockerHub.

    Thus valid examples of the `image` field are:

    *   :code:`eyra/frb-eval:3` (pulls from DockerHub)
    *   :code:`private-docker-repo:5000/eyra/frb-heimdall:1` (tries to pull from private-docker-repo:5000).

    By default, whenever an Implementation is ran as a :class:`Job`, whatever is defined in the images `Dockerfile`
    as :code:`CMD` is executed, but this can be overridden using the `command` field.
    """
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="implementations",
        help_text="Created by user",
    )
    name = models.CharField(
        max_length=255,
        unique=True,
        null=False,
        blank=False,
        help_text="Name of the implementation (e.g. FRB Evaluator v3)",
    )
    description = models.TextField(
        default="",
        blank=True,
        help_text="Description of this implementation in markdown",
    )
    image = models.CharField(
        max_length=64,
        unique=True,
        validators=[IdExistsInDockerRegistryValidator],
        help_text="Docker image (e.g. eyra/frb-eval:3)",
    )
    command = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="If specified, overrides default command as defined in Dockerfile",
    )
    algorithm = models.ForeignKey(
        Algorithm,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name='implementations',
        help_text='Implemented algorithm',
    )
    version = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Version",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['algorithm', 'version'], name='unique_version'),
        ]

    def __str__(self):
        return self.name


class Job(UUIDModel):
    """
    A `Job` represents a run of an :class:`Implementation`. It keeps track of the status, start & stop times,
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
    implementation = models.ForeignKey(
        Implementation,
        on_delete=models.CASCADE,
        help_text="Implementation being run",
    )
    output = models.ForeignKey(
        DataFile,
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
        return {job_input.input.name: job_input.data_file.pk for job_input in self.inputs.all()}


class JobInput(UUIDModel):
    """
    Input of a :class:`Job`, a link between the :class:`Input` of an :class:`Implementation` and a specific
    :class:`~comic.eyra_data.models.DataFile`.
    """
    input = models.ForeignKey(
        Input,
        on_delete=models.CASCADE,
        related_name='+',
        help_text="Input of implementation",
    )
    data_file = models.ForeignKey(
        DataFile,
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
