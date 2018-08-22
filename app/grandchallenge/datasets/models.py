# -*- coding: utf-8 -*-
from django.db import models

from grandchallenge.cases.models import Image, Annotation
from grandchallenge.challenges.models import Challenge
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.urlresolvers import reverse


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
        if self._state.adding:
            self.full_clean()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "annotations:imageset-detail",
            kwargs={
                "challenge_short_name": self.challenge.short_name,
                "pk": self.pk,
            },
        )

    class Meta:
        unique_together = ("challenge", "phase")


class AnnotationSet(UUIDModel):
    PREDICTION = "P"
    GROUNDTRUTH = "G"

    KIND_CHOICES = ((PREDICTION, "Prediction"), (GROUNDTRUTH, "Ground Truth"))

    base = models.ForeignKey(to=ImageSet, on_delete=models.CASCADE)
    annotations = models.ManyToManyField(
        to=Annotation, related_name="annotationsets"
    )
    kind = models.CharField(
        max_length=1, default=GROUNDTRUTH, choices=KIND_CHOICES
    )
