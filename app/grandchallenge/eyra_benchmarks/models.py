import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from grandchallenge.eyra_datasets.models import DataSet
from grandchallenge.eyra_evaluators.models import Evaluator

logger = logging.getLogger(__name__)


class Benchmark(models.Model):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    description = models.TextField(
        default="",
        blank=True,
        help_text="Description of this project in markdown.",
    )
    title = models.CharField(
        max_length=64,
        blank=False,
        help_text=(
            "The title of the challenge"
        ),
    )
    evaluator = models.ForeignKey(Evaluator, on_delete=models.SET_NULL, null=True, related_name='benchmarks')
    training_dataset = models.ForeignKey(DataSet, on_delete=models.SET_NULL, null=True, related_name='benchmarks_training')
    test_dataset = models.ForeignKey(DataSet, on_delete=models.SET_NULL, null=True, related_name='benchmarks_test')

    def clean(self):
        if self.training_dataset and not self.training_dataset.is_public:
            raise ValidationError("Training dataset should be public.")

    def __str__(self):
        """ string representation for this object"""
        return self.title

    class Meta:
        verbose_name = "benchmark"
        verbose_name_plural = "benchmarks"


