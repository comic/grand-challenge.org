from collections.abc import Iterable
from pathlib import Path

from django import template
from django.template.loader import render_to_string

from grandchallenge.components.models import (
    ComponentInterfaceValue,
    InterfaceKindChoices,
)

register = template.Library()

CIV_PARTIALS = Path("grandchallenge/partials/component_interface_values")


@register.filter
def sort_civs(civs: Iterable[ComponentInterfaceValue]):
    values = []
    charts = []
    thumbnails = []
    images = []
    files = []
    residual = []

    for v in civs:
        if v.value is not None:
            if v.interface.kind == InterfaceKindChoices.CHART:
                charts.append(v)
            else:
                values.append(v)
        elif v.file:
            if v.interface.kind in (
                InterfaceKindChoices.THUMBNAIL_PNG,
                InterfaceKindChoices.THUMBNAIL_JPG,
            ):
                thumbnails.append(v)
            else:
                files.append(v)
        elif v.image:
            images.append(v)
        else:
            residual.append(v)

    return [*values, *thumbnails, *charts, *files, *images, *residual]


@register.simple_tag
def civ(component_interface_value):
    template_name = _get_civ_template(component_interface_value)

    return render_to_string(
        template_name=str(CIV_PARTIALS / template_name),
        context={"civ": component_interface_value},
    )


@register.simple_tag
def civ_inline(component_interface_value):
    template_name = _get_civ_template(component_interface_value)

    if (
        component_interface_value.interface.kind
        in [
            InterfaceKindChoices.BOOL,
            InterfaceKindChoices.FLOAT,
            InterfaceKindChoices.INTEGER,
            InterfaceKindChoices.STRING,
        ]
        and component_interface_value.value is not None
    ):
        template_name = "value_preview.html"

    return render_to_string(
        template_name=str(CIV_PARTIALS / "inline" / template_name),
        context={"civ": component_interface_value},
    )


def _get_civ_template(component_interface_value) -> str:
    interface = component_interface_value.interface

    if component_interface_value.value is not None:
        if interface.kind == InterfaceKindChoices.CHART:
            return "value_chart.html"

        return "value.html"

    if component_interface_value.file:
        if interface.kind in (
            InterfaceKindChoices.THUMBNAIL_JPG,
            InterfaceKindChoices.THUMBNAIL_PNG,
        ):
            return "file_thumbnail.html"

        return "file.html"

    if component_interface_value.image:
        return "image.html"

    return "fallback.html"
