# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models

from grandchallenge.core.models import UUIDModel


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
    bucket = models.CharField(max_length=64, editable=False, blank=False)
    parent = models.CharField(max_length=512, editable=False)
    name = models.CharField(max_length=64, editable=False)
    uploaded_name = models.CharField(max_length=64, editable=False)
    sha256 = models.CharField(max_length=71, editable=False)

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.bucket = self.bucket or self._default_bucket_name
            self.name = self.name or self._default_name

        super().save(*args, **kwargs)

    @property
    def _default_bucket_name(self):
        return settings.MINIO_DEFAULT_BUCKET_NAME

    @property
    def _default_name(self):
        return 'object'
