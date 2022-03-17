from django.contrib.auth import get_user_model
from django.db import models
from guardian.shortcuts import assign_perm

from grandchallenge.core.models import TitleSlugDescriptionModel, UUIDModel
from grandchallenge.core.validators import JSONValidator


class ImagePort(models.TextChoices):
    MAIN = "M", "Main"
    SECONDARY = "S", "Secondary"
    TERTIARY = "TERTIARY", "Tertiary"
    QUATERNARY = "QUATERNARY", "Quaternary"
    QUINARY = "QUINARY", "Quinary"
    SENARY = "SENARY", "Senary"
    SEPTENARY = "SEPTENARY", "Septenary"
    OCTONARY = "OCTONARY", "Octonary"
    NONARY = "NONARY", "Nonary"
    DENARY = "DENARY", "Denary"


HANGING_PROTOCOL_SCHEMA = {
    "definitions": {},
    "$schema": "http://json-schema.org/draft-06/schema#",
    "title": "The Hanging Protocol Schema",
    "type": "array",
    "contains": {
        "type": "object",
        "properties": {
            "viewport_name": {
                "type": "string",
                "pattern": "^main$",
            },
        },
    },
    "items": {
        "type": "object",
        "title": "The Layout Object Schema",
        "required": ["viewport_name"],
        "properties": {
            "viewport_name": {
                "type": "string",
                "enum": [port.lower() for port in ImagePort.labels],
            },
            "x": {
                "type": "integer",
            },
            "y": {
                "type": "integer",
            },
            "w": {
                "type": "integer",
            },
            "h": {
                "type": "integer",
            },
            "fullsizable": {
                "type": "boolean",
            },
            "draggable": {
                "type": "boolean",
            },
            "selectable": {
                "type": "boolean",
            },
            "order": {
                "type": "integer",
            },
        },
    },
    "minItems": 1,
    "uniqueItems": True,
}


class HangingProtocol(UUIDModel, TitleSlugDescriptionModel):
    creator = models.ForeignKey(
        get_user_model(), null=True, on_delete=models.SET_NULL
    )
    json = models.JSONField(
        blank=False,
        validators=[JSONValidator(schema=HANGING_PROTOCOL_SCHEMA)],
    )

    class Meta(TitleSlugDescriptionModel.Meta, UUIDModel.Meta):
        ordering = ("title",)

    def __str__(self):
        return f"{self.title} (created by {self.creator})"

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding and self.creator:
            assign_perm(
                f"{self._meta.app_label}.change_{self._meta.model_name}",
                self.creator,
                self,
            )
