# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models

from grandchallenge.cases.models import Image, RawImageUploadSession
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

    @property
    def image_index(self):
        return {i.sorter_key: i for i in self.images.all()}

    @property
    def images_with_keys(self):
        return [
            {"key": key, "image": self.image_index[key]}
            for key in sorted(self.image_index)
        ]

    def save(self, *args, **kwargs):
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

    def __str__(self):
        return (
            f"{self.get_kind_display()} annotation set, "
            f"{len(self.images.all())} images, "
            f"created by {self.creator}"
        )

    @property
    def annotation_index(self):
        return {i.sorter_key: i for i in self.images.all()}

    @property
    def missing_annotations(self):
        base_index = self.base.image_index
        annotation_index = self.annotation_index

        missing = base_index.keys() - annotation_index.keys()

        return [
            {"key": key, "base": base_index[key]} for key in sorted(missing)
        ]

    @property
    def extra_annotations(self):
        base_index = self.base.image_index
        annotation_index = self.annotation_index

        extra = annotation_index.keys() - base_index.keys()

        return [
            {"key": key, "annotation": annotation_index[key]}
            for key in sorted(extra)
        ]

    @property
    def matched_images(self):
        base_index = self.base.image_index
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
