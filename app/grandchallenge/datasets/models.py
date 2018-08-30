# -*- coding: utf-8 -*-
from os.path import commonprefix

from django.conf import settings
from django.db import models

from grandchallenge.cases.models import (
    Image,
    RawImageUploadSession,
    RawImageFile,
)
from grandchallenge.challenges.models import Challenge
from grandchallenge.container_exec.models import ContainerExecJobModel
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.evaluation.models import Submission
from grandchallenge.jqfileupload.models import StagedFile


class IndexMixin:
    @property
    def index(self):
        images = self.images.all()
        common_prefix = commonprefix([i.name for i in images])
        return {i.sorter_key(start=len(common_prefix)): i for i in images}


class ImageSet(UUIDModel, IndexMixin):
    TRAINING = "TRN"
    TESTING = "TST"

    PHASE_CHOICES = ((TRAINING, "Training"), (TESTING, "Testing"))

    challenge = models.ForeignKey(to=Challenge, on_delete=models.CASCADE)
    phase = models.CharField(
        max_length=3, default=TRAINING, choices=PHASE_CHOICES
    )
    images = models.ManyToManyField(to=Image, related_name="imagesets")

    @property
    def images_with_keys(self):
        return [
            {"key": key, "image": self.index[key]}
            for key in sorted(self.index)
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


class AnnotationSet(UUIDModel, IndexMixin):
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
    submission = models.OneToOneField(
        to=Submission, null=True, on_delete=models.SET_NULL, editable=False
    )

    def __str__(self):
        return (
            f"{self.get_kind_display()} annotation set, "
            f"{len(self.images.all())} images, "
            f"created by {self.creator}"
        )

    @property
    def missing_annotations(self):
        base_index = self.base.index
        annotation_index = self.index

        missing = base_index.keys() - annotation_index.keys()

        return [
            {"key": key, "base": base_index[key]} for key in sorted(missing)
        ]

    @property
    def extra_annotations(self):
        base_index = self.base.index
        annotation_index = self.index

        extra = annotation_index.keys() - base_index.keys()

        return [
            {"key": key, "annotation": annotation_index[key]}
            for key in sorted(extra)
        ]

    @property
    def matched_images(self):
        base_index = self.base.index
        annotation_index = self.index

        matches = base_index.keys() & annotation_index.keys()

        return [
            {
                "key": key,
                "base": base_index[key],
                "annotation": annotation_index[key],
                "annotation_cirrus_link": self.create_cirrus_annotation_link(
                    base=base_index[key], annotation=annotation_index[key]
                ),
            }
            for key in sorted(matches)
        ]

    def create_cirrus_annotation_link(self, *, base: Image, annotation: Image):
        return f"{base.cirrus_link}&{settings.CIRRUS_ANNOATION_QUERY_PARAM}={annotation.pk}"

    def get_absolute_url(self):
        return reverse(
            "datasets:annotationset-detail",
            kwargs={
                "challenge_short_name": self.base.challenge.short_name,
                "pk": self.pk,
            },
        )
