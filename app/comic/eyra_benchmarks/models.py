import logging

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models

from comic.core.models import UUIDModel
from comic.eyra_algorithms.models import Job, Implementation, Interface
from comic.eyra_data.models import DataFile, DataSet

logger = logging.getLogger(__name__)


class Benchmark(UUIDModel):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    short_description = models.TextField(
        default="",
        help_text="Short description in markdown.",
    )
    description = models.TextField(
        default="",
        help_text="Description in markdown.",
    )
    data_description = models.TextField(
        default="",
        help_text="Description of the data used in this benchmark in markdown.",
    )
    truth_description = models.TextField(
        default="",
        help_text="Description of the truth data in markdown.",
    )
    metrics_description = models.TextField(
        default="",
        help_text="Description of the metrics in markdown.",
    )
    name = models.CharField(
        max_length=255,
        blank=False,
        help_text=(
            "The name of the benchmark"
        ),
        unique=True,
    )
    card_image_url = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        default="https://www.staging.eyrabenchmark.net/static/media/logo.3fc4ddae.png",
        help_text=(
            "Benchmark card image"
        ),
    )
    banner_image_url = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        default="https://www.staging.eyrabenchmark.net/static/media/logo.3fc4ddae.png",
        help_text=(
            "Benchmark banner image"
        ),
    )

    evaluator = models.ForeignKey(Implementation, on_delete=models.SET_NULL, null=True, blank=True, related_name='benchmarks')
    data_set = models.ForeignKey(DataSet, on_delete=models.SET_NULL, null=True, blank=True, related_name='benchmarks')
    interface = models.ForeignKey(Interface, on_delete=models.SET_NULL, null=True, blank=True, related_name='benchmarks')
    admin_group = models.OneToOneField(
        Group,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="benchmark",
    )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

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
