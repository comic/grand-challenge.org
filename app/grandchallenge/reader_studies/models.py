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
        return sorted(self.study_image_names) == sorted(
            self.hanging_image_names
        )

    @property
    def non_unique_study_image_names(self):
        return [
            name
            for name, count in Counter(self.study_image_names).items()
            if count > 1
        ]
