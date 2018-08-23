# -*- coding: utf-8 -*-
import logging
import re

from django.conf import settings
from django.db import models

from grandchallenge.cases.models import (
    Image,
    Annotation,
    RawImageUploadSession,
)
from grandchallenge.challenges.models import Challenge
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.urlresolvers import reverse

logger = logging.getLogger(__name__)


class ImageSet(UUIDModel):
    TRAINING = "TRN"
    TESTING = "TST"

    PHASE_CHOICES = ((TRAINING, "Training"), (TESTING, "Testing"))

    challenge = models.ForeignKey(to=Challenge, on_delete=models.CASCADE)
    phase = models.CharField(
        max_length=3, default=TRAINING, choices=PHASE_CHOICES
    )
    images = models.ManyToManyField(to=Image, related_name="imagesets")

    def save(self, *args, **kwargs):
        logger.debug("Saving ImageSet")

        if self._state.adding:
            self.full_clean()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "datasets:imageset-detail",
            kwargs={
                "challenge_short_name": self.challenge.short_name,
                "pk": self.pk,
            },
        )

    class Meta:
        unique_together = ("challenge", "phase")


def get_first_int_in(s: str) -> str:
    """
    For use in filtering.

    Gets the first int in a string, and returns that string. If an int cannot
    be found, returns the lower case name split at the first full stop.
    """
    try:
        r = re.compile(r"\D*((?:\d+\.?)+)\D*")
        m = r.search(s)
        return f"{int(m.group(1).replace('.', '')):>64}"
    except AttributeError:
        return s.split(".")[0].lower()


class AnnotationSet(UUIDModel):
    PREDICTION = "P"
    GROUNDTRUTH = "G"

    KIND_CHOICES = ((PREDICTION, "Prediction"), (GROUNDTRUTH, "Ground Truth"))

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    base = models.ForeignKey(to=ImageSet, on_delete=models.CASCADE)
    kind = models.CharField(
        max_length=1, default=GROUNDTRUTH, choices=KIND_CHOICES
    )
    images = models.ManyToManyField(to=Image, related_name="annotationsets")

    @property
    def base_index(self):
        return {get_first_int_in(s.name): s for s in self.base.images.all()}

    @property
    def annotation_index(self):
        return {get_first_int_in(s.name): s for s in self.images.all()}

    @property
    def missing_annotations(self):
        base_index = self.base_index
        annotation_index = self.annotation_index

        missing = base_index.keys() - annotation_index.keys()

        return [
            {"key": key, "base": base_index[key]} for key in sorted(missing)
        ]

    @property
    def extra_annotations(self):
        base_index = self.base_index
        annotation_index = self.annotation_index

        extra = annotation_index.keys() - base_index.keys()

        return [
            {"key": key, "annotation": annotation_index[key]}
            for key in sorted(extra)
        ]

    @property
    def matched_images(self):
        base_index = self.base_index
        annotation_index = self.annotation_index

        matches = base_index.keys() & annotation_index.keys()

        return [
            {
                "key": key,
                "base": base_index[key],
                "annotation": annotation_index[key],
            }
            for key in sorted(matches)
        ]

    def get_absolute_url(self):
        return reverse(
            "datasets:annotationset-detail",
            kwargs={
                "challenge_short_name": self.base.challenge.short_name,
                "pk": self.pk,
            },
        )
