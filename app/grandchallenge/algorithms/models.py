# -*- coding: utf-8 -*-
from ckeditor.fields import RichTextField
from django.db import models
from social_django.fields import JSONField

from grandchallenge.core.models import (
    UUIDModel, CeleryJobModel, DockerImageModel
)
from grandchallenge.core.urlresolvers import reverse


class Algorithm(UUIDModel, DockerImageModel):
    description_html = RichTextField(blank=True)

    def get_absolute_url(self):
        return reverse("algorithms:detail", kwargs={"pk": self.pk})


class Job(UUIDModel, CeleryJobModel):
    algorithm = models.ForeignKey(Algorithm, on_delete=models.CASCADE)
    case = models.ForeignKey("cases.Case", on_delete=models.CASCADE)

    @property
    def container(self):
        return self.algorithm

    @property
    def input_files(self):
        return [c.file for c in self.case.casefile_set.all()]

    def get_absolute_url(self):
        return reverse("algorithms:jobs-detail", kwargs={"pk": self.pk})


class Result(UUIDModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    output = JSONField(default=dict)

    def get_absolute_url(self):
        return reverse("algorithms:results-detail", kwargs={"pk": self.pk})
