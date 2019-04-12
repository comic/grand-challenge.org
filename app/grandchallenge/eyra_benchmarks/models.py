import logging

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models

from grandchallenge.core.models import UUIDModel
from grandchallenge.eyra_algorithms.models import Job, Implementation, Interface
from grandchallenge.eyra_data.models import DataFile

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
        help_text="Description of this project in markdown.",
    )
    name = models.CharField(
        max_length=255,
        blank=False,
        help_text=(
            "The name of the benchmark"
        ),
        unique=True,
    )
    image = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        default="https://www.staging.eyrabenchmark.net/static/media/logo.3fc4ddae.png",
        help_text=(
            "Benchmark image"
        ),
    )
    evaluator = models.ForeignKey(Implementation, on_delete=models.SET_NULL, null=True, blank=True, related_name='benchmarks')
    training_data_file = models.ForeignKey(DataFile, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    training_ground_truth_data_file = models.ForeignKey(DataFile, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    test_data_file = models.ForeignKey(DataFile, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    test_ground_truth_data_file = models.ForeignKey(DataFile, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
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
            if self.test_data_file and self.test_data_file.type != self.interface.inputs.first().type:
                raise ValidationError('The types of test_data_file and benchmark interface input should match.')

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
    implementation_job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    evaluation_job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    metrics_json = JSONField(null=True, blank=True)
