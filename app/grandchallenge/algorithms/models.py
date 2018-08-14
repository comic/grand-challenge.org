# -*- coding: utf-8 -*-
from pathlib import Path

from ckeditor.fields import RichTextField
from django.contrib.postgres.fields import JSONField
from django.db import models

from grandchallenge.core.models import UUIDModel
from grandchallenge.container_exec.models import (
    CeleryJobModel, DockerImageModel,
)
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.container_exec.backends.dockermachine.evaluator import (
    Evaluator
)


class Algorithm(UUIDModel, DockerImageModel):
    description_html = RichTextField(blank=True)

    def get_absolute_url(self):
        return reverse("algorithms:detail", kwargs={"pk": self.pk})


class Result(UUIDModel):
    job = models.OneToOneField('Job', null=True, on_delete=models.CASCADE)
    output = JSONField(default=dict)

    def get_absolute_url(self):
        return reverse("algorithms:results-detail", kwargs={"pk": self.pk})


class AlgorithmExecutor(Evaluator):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            results_file=Path("/output/results.json"),
            **kwargs
        )


class Job(UUIDModel, CeleryJobModel):
    algorithm = models.ForeignKey(Algorithm, on_delete=models.CASCADE)
    case = models.ForeignKey("cases.Case", on_delete=models.CASCADE)

    @property
    def container(self):
        return self.algorithm

    @property
    def input_files(self):
        return [c.file for c in self.case.casefile_set.all()]

    @property
    def evaluator_cls(self):
        return AlgorithmExecutor

    def create_result(self, *, result: dict):
        Result.objects.create(job=self, output=result)

    def get_absolute_url(self):
        return reverse("algorithms:jobs-detail", kwargs={"pk": self.pk})
