from django.contrib.auth import get_user_model
from django.db import models
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import assign_perm

from grandchallenge.core.models import TitleSlugDescriptionModel, UUIDModel
from grandchallenge.core.validators import JSONValidator


class ViewportNames(models.TextChoices):
    main = "main"
    secondary = "secondary"
    tertiary = "tertiary"
    quaternary = "quaternary"
    quinary = "quinary"
    senary = "senary"
    septenary = "septenary"
    octonary = "octonary"
    nonary = "nonary"
    denary = "denary"
    undenary = "undenary"
    duodenary = "duodenary"
    tredenary = "tredenary"
    quattuordenary = "quattuordenary"
    quindenary = "quindenary"
    sexdenary = "sexdenary"
    septendenary = "septendenary"
    octodenary = "octodenary"
    novemdenary = "novemdenary"
    vigintenary = "vigintenary"


class Orientation(models.TextChoices):
    axial = "axial"
    coronal = "coronal"
    sagittal = "sagittal"


HANGING_PROTOCOL_SCHEMA = {
    "definitions": {},
    "$schema": "http://json-schema.org/draft-07/schema#",
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
            },
            "specialized_view": {
                "type": "string",
                "enum": ["minimap", "3D-sideview", "openseadragon"],
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
            "linkable": {
                "type": "boolean",
            },
            "order": {
                "type": "integer",
            },
            "show_current_slice": {
                "type": "boolean",
            },
            "show_mouse_coordinate": {
                "type": "boolean",
            },
            "show_mouse_voxel_value": {
                "type": "boolean",
            },
            "label": {
                "type": "string",
            },
            "orientation": {
                "type": "string",
                "enum": Orientation.values,
            },
            "parent_id": {
                "type": "string",
                "enum": ViewportNames.values,
            },
            "opacity": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
            "slice_plane_indicator": {
                "type": "string",
                "enum": ViewportNames.values,
            },
            "slice_plane_indicator_fade_ms": {
                "type": "number",
                "minimum": 0,
            },
        },
        "additionalProperties": False,
        "allOf": [
            {
                "if": {
                    "required": ["specialized_view"],
                    "properties": {
                        "specialized_view": {
                            "enum": ["minimap", "3D-sideview"]
                        },
                    },
                },
                "then": {
                    "required": ["parent_id"],
                    "properties": {
                        "viewport_name": {
                            "type": "string",
                            "pattern": "^[a-zA-Z0-9_]+$",
                        }
                    },
                },
                "else": {
                    "properties": {
                        "viewport_name": {
                            "type": "string",
                            "enum": ViewportNames.values,
                        }
                    }
                },
            },
            {
                "if": {
                    "required": ["specialized_view"],
                    "properties": {
                        "specialized_view": {"const": "3D-sideview"}
                    },
                },
                "then": {"required": ["orientation"]},
            },
        ],
    },
    "minItems": 1,
    "uniqueItems": True,
}


VIEW_CONTENT_SCHEMA = {
    "definitions": {},
    "$schema": "http://json-schema.org/draft-06/schema#",
    "title": "The Display Port Mapping Schema",
    "type": "object",
    "properties": {
        port.lower(): {
            "type": "array",
            "contains": {"type": "string"},
            "minItems": 1,
            "uniqueItems": True,
        }
        for port in ViewportNames.values
    },
    "additionalProperties": False,
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


class HangingProtocolUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(
        HangingProtocol, on_delete=models.CASCADE
    )


class HangingProtocolGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(
        HangingProtocol, on_delete=models.CASCADE
    )


class ViewContentMixin(models.Model):
    view_content = models.JSONField(
        blank=True,
        default=dict,
        validators=[JSONValidator(schema=VIEW_CONTENT_SCHEMA)],
    )

    class Meta:
        abstract = True
