import logging
import os

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models

from comic.core.models import UUIDModel
from comic.eyra_algorithms.models import Job, Implementation, Interface
from comic.eyra_data.models import DataFile, DataSet

logger = logging.getLogger(__name__)


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

    `interface` field:
        The interface for user :class:`Submission`\s.

    `evaluator` field:
        The evaluator field sets which :class:`~comic.eyra_algorithms.models.Implementation` (docker image) is
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
    evaluator = models.ForeignKey(
        Implementation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='benchmarks',
        help_text="Evaluation implementation. Generates " +
                  "OutputMetrics using ground truth and output of the previous step"
    )
    data_set = models.ForeignKey(
        DataSet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='benchmarks',
        help_text="Data set used in this benchmark",
    )
    interface = models.ForeignKey(
        Interface,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='benchmarks',
        help_text="Interface for submissions to this benchmark"
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
        from comic.eyra_benchmarks.utils import set_benchmark_admin_group, set_benchmark_default_permissions
        set_benchmark_admin_group(self)
        self.full_clean()
        super().save(*args, **kwargs)
        set_benchmark_default_permissions(self)

    def clean(self):
        if self.evaluator:
            eval_interface = self.evaluator.algorithm.interface
            if eval_interface.output_type.name != 'OutputMetrics':
                raise ValidationError('Benchmark evaluator should have OutputMetrics as output data type.')
            input_names = [inp.name for inp in eval_interface.inputs.all()]
            if len(input_names) != 2 or 'ground_truth' not in input_names or 'implementation_output' not in input_names:
                raise ValidationError('Benchmark evaluator should have "ground_truth" and "implementation_output" as inputs.')
            if self.interface and self.interface.output_type != eval_interface.inputs.get(name='implementation_output').type:
                raise ValidationError(
                    'Benchmark interface output type and evaluator input type for "implementation_output" should match.')

        if self.interface:
            if self.interface.inputs.count() != 1:
                raise ValidationError('Benchmark interface should have a single input.')
            if self.data_set and self.data_set.public_test_data_file.type != self.interface.inputs.first().type:
                raise ValidationError('The types of data_set.test_data_file and benchmark interface input should match.')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "benchmark"
        verbose_name_plural = "benchmarks"


class Submission(UUIDModel):
    """
    A `Submission` indicates an (user-created) :class:`~comic.eyra_algorithms.models.Implementation` tested against a
    :class:`Benchmark`. Whenever a `Submission` is created, two :class:`Jobs <comic.eyra_algorithms.models.Job>`
    are created: the implementation_job (which runs first) and the evaluation_job (which runs second, using the output
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
    implementation = models.ForeignKey(Implementation, on_delete=models.CASCADE, related_name='submissions')
    implementation_job = models.ForeignKey(Job, on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    evaluation_job = models.ForeignKey(Job, on_delete=models.CASCADE, null=True, blank=True, related_name='+')
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
