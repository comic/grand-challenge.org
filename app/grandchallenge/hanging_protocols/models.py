from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import format_html
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import assign_perm

from grandchallenge.components.models import ComponentInterface, InterfaceKind
from grandchallenge.core.models import TitleSlugDescriptionModel, UUIDModel
from grandchallenge.core.validators import JSONValidator
from grandchallenge.subdomains.utils import reverse


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
                "enum": [
                    "minimap",
                    "3D-sideview",
                    "clientside",
                    "intensity-over-time-chart",
                ],
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
                            "enum": [
                                "minimap",
                                "3D-sideview",
                            ]
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
            {
                "if": {
                    "required": ["specialized_view"],
                    "properties": {
                        "specialized_view": {
                            "const": "intensity-over-time-chart"
                        }
                    },
                },
                "then": {"required": ["parent_id"]},
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

    @property
    def svg_icon(self) -> str:
        width = len(self.json)
        height = 1

        if "x" in self.json[0]:
            width = max(vi["x"] + vi["w"] for vi in self.json)
            height = max(vi["y"] + vi["h"] for vi in self.json)

        width_px = 32
        height_px = 18
        stroke_width = width_px * 0.05
        padding = stroke_width / 2

        svg = format_html(
            '<svg width="{width_px}" height="{height_px}" fill-opacity="0">',
            width_px=width_px,
            height_px=height_px,
        )

        for i, vi in enumerate(self.json):
            w = (width_px - 2 * padding) / len(self.json)
            h = height_px - 2 * padding
            x = padding + i * w
            y = padding

            if "x" in self.json[0]:
                w = (width_px - 2 * padding) * vi["w"] / width
                h = (height_px - 2 * padding) * vi["h"] / height
                x = padding + (width_px - 2 * padding) * vi["x"] / width
                y = padding + (height_px - 2 * padding) * vi["y"] / height

            svg += format_html(
                '<rect x="{x}" y="{y}" width="{width}" height="{height}" stroke-width="{stroke_width}" />',
                x=x,
                y=y,
                width=w,
                height=h,
                stroke_width=stroke_width,
            )

        svg += format_html("</svg>")

        return svg

    def get_absolute_url(self):
        return reverse("hanging-protocols:detail", kwargs={"slug": self.slug})


class HangingProtocolUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(
        HangingProtocol, on_delete=models.CASCADE
    )


class HangingProtocolGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(
        HangingProtocol, on_delete=models.CASCADE
    )


class HangingProtocolMixin(models.Model):
    view_content = models.JSONField(
        blank=True,
        default=dict,
        validators=[JSONValidator(schema=VIEW_CONTENT_SCHEMA)],
    )
    hanging_protocol = models.ForeignKey(
        "hanging_protocols.HangingProtocol",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=(
            "Indicate which Component Interfaces need to be displayed in "
            'which image port. E.g. {"main": ["interface1"]}. The first '
            "item in the list of interfaces will be the main image in "
            "the image port. The first overlay type interface thereafter "
            "will be rendered as an overlay. For now, any other items "
            "will be ignored by the viewer."
        ),
    )

    def clean(self):
        super().clean()

        self.check_consistent_viewports()
        self.check_all_interfaces_in_view_content_exist()

    def check_consistent_viewports(self):
        if self.view_content and self.hanging_protocol:
            if set(self.view_content.keys()) != {
                x["viewport_name"] for x in self.hanging_protocol.json
            }:
                raise ValidationError(
                    "Image ports in view_content do not match "
                    "those in the selected hanging protocol."
                )

    def check_all_interfaces_in_view_content_exist(self):
        if not hasattr(self.view_content, "items"):
            raise ValidationError("View content is invalid")

        for viewport, slugs in self.view_content.items():
            viewport_interfaces = ComponentInterface.objects.filter(
                slug__in=slugs
            )

            if set(slugs) != {i.slug for i in viewport_interfaces}:
                raise ValidationError(
                    f"Unknown interfaces in view content for viewport {viewport}: {', '.join(slugs)}"
                )

            image_interfaces = [
                i
                for i in viewport_interfaces
                if i.kind == InterfaceKind.InterfaceKindChoices.IMAGE
            ]

            if len(image_interfaces) > 1:
                raise ValidationError(
                    "Maximum of one image interface is allowed per viewport, "
                    f"got {len(image_interfaces)} for viewport {viewport}: "
                    f"{', '.join(i.slug for i in image_interfaces)}"
                )

            mandatory_isolation_interfaces = [
                i
                for i in viewport_interfaces
                if i.kind in InterfaceKind.interface_type_mandatory_isolation()
            ]

            if len(mandatory_isolation_interfaces) > 1 or (
                len(mandatory_isolation_interfaces) == 1
                and len(viewport_interfaces) > 1
            ):
                raise ValidationError(
                    "Some of the selected interfaces can only be displayed in isolation, "
                    f"found {len(mandatory_isolation_interfaces)} for viewport {viewport}: "
                    f"{', '.join(i.slug for i in mandatory_isolation_interfaces)}"
                )

            undisplayable_interfaces = [
                i
                for i in viewport_interfaces
                if i.kind in InterfaceKind.interface_type_undisplayable()
            ]

            if len(undisplayable_interfaces) > 0:
                raise ValidationError(
                    "Some of the selected interfaces cannot be displayed, "
                    f"found {len(undisplayable_interfaces)} for viewport {viewport}: "
                    f"{', '.join(i.slug for i in undisplayable_interfaces)}"
                )

    class Meta:
        abstract = True
