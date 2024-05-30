from pathlib import Path

from django import template
from django.template.loader import render_to_string

from grandchallenge.components.models import (
    InterfaceKindChoices,
    InterfaceSuperKindChoices,
)

register = template.Library()

CIV_PARTIALS = Path("grandchallenge/partials/component_interface_values")


@register.simple_tag
def civ(component_interface_value):
    template_path = _get_civ_render_template(component_interface_value)

    return render_to_string(
        template_name=str(CIV_PARTIALS / template_path),
        context={"civ": component_interface_value},
    )


@register.simple_tag
def civ_inline(component_interface_value):
    template_path = _get_civ_render_template(component_interface_value)

    if (
        component_interface_value.interface.kind
        in [
            InterfaceKindChoices.BOOL,
            InterfaceKindChoices.FLOAT,
            InterfaceKindChoices.INTEGER,
            InterfaceKindChoices.STRING,
        ]
        and component_interface_value.interface.store_in_database
    ):
        template_path = "json_preview.html"

    return render_to_string(
        template_name=str(CIV_PARTIALS / "inline" / template_path),
        context={"civ": component_interface_value},
    )


def _get_civ_render_template(component_interface_value) -> str:
    interface = component_interface_value.interface

    if interface.super_kind == InterfaceSuperKindChoices.VALUE:
        if interface.kind == InterfaceKindChoices.CHART:
            return "vega_lite_chart.html"

        return "json.html"

    if interface.super_kind == InterfaceSuperKindChoices.FILE:
        if interface.kind in (
            InterfaceKindChoices.THUMBNAIL_JPG,
            InterfaceKindChoices.THUMBNAIL_PNG,
        ):
            return "thumbnail.html"

        return "file.html"

    if interface.super_kind == InterfaceSuperKindChoices.IMAGE:
        return "image.html"

    return "fallback.html"
