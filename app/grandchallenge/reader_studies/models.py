from collections import Counter

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.db import models
from django_extensions.db.models import TitleSlugDescriptionModel

from grandchallenge.core.models import UUIDModel
from grandchallenge.core.validators import JSONSchemaValidator
from grandchallenge.subdomains.utils import reverse


HANGING_LIST_SCHEMA = {
    "definitions": {},
    "$schema": "http://json-schema.org/draft-06/schema#",
    "type": "array",
    "title": "The Hanging List Schema",
    "items": {
        "$id": "#/items",
        "type": "object",
        "title": "The Items Schema",
        "required": ["main"],
        "additionalProperties": False,
        "properties": {
            "main": {
                "$id": "#/items/properties/main",
                "type": "string",
                "title": "The Main Schema",
                "default": "",
                "examples": ["im1.mhd"],
                "pattern": "^(.*)$",
            },
            "secondary": {
                "$id": "#/items/properties/secondary",
                "type": "string",
                "title": "The Secondary Schema",
                "default": "",
                "examples": ["im2.mhd"],
                "pattern": "^(.*)$",
            },
        },
    },
}


class ReaderStudy(UUIDModel, TitleSlugDescriptionModel):
    creator = models.ForeignKey(
        get_user_model(), null=True, on_delete=models.SET_NULL
    )
    readers = models.ManyToManyField(
        get_user_model(), related_name="readerstudies"
    )
    images = models.ManyToManyField(
        "cases.Image", related_name="readerstudies"
    )

    # A hanging_list is a list of dictionaries where the keys are the
    # view names, and the values are the filenames to place there.
    hanging_list = JSONField(
        default=list,
        blank=True,
        validators=[JSONSchemaValidator(schema=HANGING_LIST_SCHEMA)],
    )

    class Meta(UUIDModel.Meta, TitleSlugDescriptionModel.Meta):
        verbose_name_plural = "reader studies"

    def get_absolute_url(self):
        return reverse("reader-studies:detail", kwargs={"slug": self.slug})

    @property
    def study_image_names(self):
        return [im.name for im in self.images.all()]

    @property
    def hanging_image_names(self):
        return [
            name for hanging in self.hanging_list for name in hanging.values()
        ]

    @property
    def hanging_list_valid(self):
        """
        Test that all of the study images are included in the hanging list
        exactly once.
        """
        return sorted(self.study_image_names) == sorted(
            self.hanging_image_names
        )

    @property
    def non_unique_study_image_names(self):
        """
        Get all of the image names that are non-unique for this ReaderStudy
        """
        return [
            name
            for name, count in Counter(self.study_image_names).items()
            if count > 1
        ]

    @property
    def is_valid(self):
        """ Is this ReaderStudy valid? """
        return (
            self.hanging_list_valid
            and len(self.non_unique_study_image_names) == 0
        )

    @property
    def hanging_list_images(self):
        """
        Substitutes the image name for the image detail api url for each image
        defined in the hanging list.
        """
        if not self.is_valid:
            return None

        study_images = {
            im.name: reverse("api:image-detail", kwargs={"pk": im.pk})
            for im in self.images.all()
        }

        hanging_list_images = [
            {view: study_images.get(name) for view, name in hanging.items()}
            for hanging in self.hanging_list
        ]

        return hanging_list_images


class Question(UUIDModel):
    ANSWER_TYPE_BOOL = "B"
    ANSWER_TYPE_STRING = "S"
    ANSWER_TYPE_FLOAT = "F"
    ANSWER_TYPE_CHOICES = (
        (ANSWER_TYPE_BOOL, "Bool"),
        (ANSWER_TYPE_STRING, "String"),
        (ANSWER_TYPE_FLOAT, "Float"),
    )

    reader_study = models.ForeignKey(ReaderStudy, on_delete=models.CASCADE)
    question_text = models.TextField()
    answer_type = models.CharField(max_length=1, choices=ANSWER_TYPE_CHOICES)
    order = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return f"{self.question_text} ({self.get_answer_type_display()})"

    class Meta:
        ordering = ("order", "created")


class Answer(UUIDModel):
    creator = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    hanging_images = JSONField()
    json = JSONField()
