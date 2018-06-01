# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models
from social_django.fields import JSONField

from grandchallenge.core.models import UUIDModel, CeleryJobModel
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.evaluation.validators import ExtensionValidator, \
    MimeTypeValidator


def algorithm_image_path(instance, filename):
    return (
        f'algorithms/{instance.pk}/{filename}'
    )


def algorithm_description_path(instance, filename):
    return (
        f'algorithm-descriptions/{instance.pk}/{filename}'
    )


class Algorithm(UUIDModel):
    # TODO: This class is mostly duplicate from evaluation/models.py.
    # TODO: make a mixin for DockerImage, generalize docker_image_path to work with instance
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )

    image = models.FileField(
        upload_to=algorithm_image_path,
        validators=[ExtensionValidator(allowed_extensions=('.tar',))],
        help_text=(
            'Tar archive of the container image produced from the command '
            '`docker save IMAGE > IMAGE.tar`. See '
            'https://docs.docker.com/engine/reference/commandline/save/'
        ),
    )
    image_sha256 = models.CharField(editable=False, max_length=71)

    # TODO: add that this is an ipynb to the help_text
    description = models.FileField(
        upload_to=algorithm_description_path,
        validators=[
            MimeTypeValidator(allowed_types=('text/plain',))
        ],
        blank=True,
    )

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
