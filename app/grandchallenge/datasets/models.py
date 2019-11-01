import logging
import re
from os.path import commonprefix
from typing import Union

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models

from grandchallenge.cases.models import Image
from grandchallenge.challenges.models import Challenge
from grandchallenge.core.models import UUIDModel
from grandchallenge.evaluation.models import Submission
from grandchallenge.subdomains.utils import reverse

logger = logging.getLogger(__name__)


def find_first_int(*, instr) -> tuple:
    """
    For use in filtering.

    Gets the first int in the instr, and returns that string.
    If an int cannot be found, returns the lower case name split at the
    first full stop.
    """
    try:
        r = re.compile(r"\D*((?:\d+\.?)+)\D*")
        m = r.search(instr)
        key = f"{int(m.group(1).replace('.', '')):>64}"
    except AttributeError:
        key = instr.split(".")[0].lower()

    return key


class IndexMixin:
    def index(self: Union["ImageSet", "AnnotationSet"], include_shape=True):
        images = self.images.all()
        common_prefix = commonprefix([i.name.lower() for i in images])
        if include_shape:
            return {
                (
                    find_first_int(instr=i.name[len(common_prefix) :]),
                    *i.shape,
                ): i
                for i in images
            }
        else:
            return {
                find_first_int(instr=i.name[len(common_prefix) :]): i
                for i in images
            }


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
            {"key": key, "image": self.index()[key]}
            for key in sorted(self.index())
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
    labels = JSONField(blank=True, default=dict, editable=False)
    submission = models.OneToOneField(
        to=Submission, null=True, on_delete=models.SET_NULL, editable=False
    )

    def __str__(self):
        return (
            f"{self.get_kind_display()} annotation set, "
            f"{len(self.images.all())} images, "
            f"{len(self.labels)} labels, "
            f"created by {self.creator}"
        )

    @property
    def label_index(self) -> dict:
        join_key = (
            self.base.challenge.evaluation_config.submission_join_key.lower()
        )

        try:
            common_prefix = commonprefix(
                [str(l[join_key]).lower() for l in self.labels]
            )
        except KeyError:
            logger.warning(
                f"The join key, {join_key}, was not found for "
                f"{self.base.challenge}"
            )
            return {}

        return {
            find_first_int(instr=str(l[join_key])[len(common_prefix) :]): l
            for l in self.labels
        }

    @property
    def missing_annotations(self):
        base_index = self.base.index()
        annotation_index = self.index()

        missing = base_index.keys() - annotation_index.keys()

        return [
            {"key": key, "base": base_index[key]} for key in sorted(missing)
        ]

    @property
    def extra_annotations(self):
        base_index = self.base.index()
        annotation_index = self.index()

        extra = annotation_index.keys() - base_index.keys()

        return [
            {"key": key, "annotation": annotation_index[key]}
            for key in sorted(extra)
        ]

    @property
    def matched_images(self):
        base_index = self.base.index()
        annotation_index = self.index()

        matches = base_index.keys() & annotation_index.keys()

        return [
            {
                "key": key,
                "base": base_index[key],
                "annotation": annotation_index[key],
            }
            for key in sorted(matches)
        ]

    @property
    def missing_labels(self):
        base_index = self.base.index(include_shape=False)
        label_index = self.label_index

        missing = base_index.keys() - label_index.keys()

        return [
            {"key": key, "base": base_index[key]} for key in sorted(missing)
        ]

    @property
    def extra_labels(self):
        base_index = self.base.index(include_shape=False)
        label_index = self.label_index

        extra = label_index.keys() - base_index.keys()

        return [
            {"key": key, "label": label_index[key]} for key in sorted(extra)
        ]

    @property
    def matched_labels(self):
        base_index = self.base.index(include_shape=False)
        label_index = self.label_index

        matches = base_index.keys() & label_index.keys()

        return [
            {"key": key, "base": base_index[key], "label": label_index[key]}
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
