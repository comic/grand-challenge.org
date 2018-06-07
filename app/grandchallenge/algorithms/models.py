# -*- coding: utf-8 -*-
from django.db import models
from social_django.fields import JSONField

from grandchallenge.core.models import (
    UUIDModel, CeleryJobModel, DockerImageModel
)
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.evaluation.validators import MimeTypeValidator


def algorithm_description_path(instance, filename):
    return (
        f'algorithm-descriptions/{instance.pk}/{filename}'
    )


class Algorithm(UUIDModel, DockerImageModel):
    # TODO: Split out the ipynb description as a separate object
    # TODO: add that this is an ipynb to the help_text
    #  TODO: should the ipynb be downloadable?
    description = models.FileField(
        upload_to=algorithm_description_path,
        validators=[
            MimeTypeValidator(allowed_types=('text/plain',))
        ],
        blank=True,
    )
    description_html = models.TextField(blank=True, editable=False)

    def get_absolute_url(self):
        return reverse("algorithms:detail", kwargs={"pk": self.pk})


class Job(UUIDModel, CeleryJobModel):
    algorithm = models.ForeignKey(Algorithm, on_delete=models.CASCADE)
    case = models.ForeignKey("cases.Case", on_delete=models.CASCADE)

    def get_absolute_url(self):
        return reverse("algorithms:jobs-detail", kwargs={"pk": self.pk})


class Result(UUIDModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    output = JSONField(default=dict)

    def get_absolute_url(self):
        return reverse("algorithms:results-detail", kwargs={"pk": self.pk})
