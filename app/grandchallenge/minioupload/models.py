# -*- coding: utf-8 -*-
from django.db import models

from grandchallenge.evaluation.models import UUIDModel


class MinioFile(UUIDModel):
    INITIALISED = 'I'
    UPLOADED = 'U'
    FAILED = 'F'

    UPLOAD_STATES = (
        (INITIALISED, 'Initialised'),
        (UPLOADED, 'Uploaded'),
        (FAILED, 'Failed'),
    )

    state = models.CharField(
        max_length=1,
        choices=UPLOAD_STATES,
        default=INITIALISED,
        editable=False,
    )
    bucket = models.CharField(max_length=64, editable=False)
    path = models.CharField(max_length=512, editable=False)
    sha256 = models.CharField(max_length=71, editable=False)
