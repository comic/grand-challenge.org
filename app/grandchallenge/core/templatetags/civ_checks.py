from pathlib import Path

from django import template

from grandchallenge.components.models import (
    ComponentInterfaceValue,
    InterfaceKindChoices,
    InterfaceSuperKindChoices,
)

register = template.Library()

CIV_PARTIALS = Path("grandchallenge/partials/component_interface_values")


@register.filter
def civ_render_template(civ: ComponentInterfaceValue) -> Path | None:
    return _get_civ_render_template(civ, partials_path=CIV_PARTIALS)


@register.filter
def civ_inline_render_template(civ: ComponentInterfaceValue) -> Path | None:
    return _get_civ_render_template(civ, partials_path=CIV_PARTIALS / "inline")


def _get_civ_render_template(
    civ: ComponentInterfaceValue, partials_path: Path
):
    interface = civ.interface

    if interface.super_kind == InterfaceSuperKindChoices.VALUE:
        if interface.kind == InterfaceKindChoices.CHART:
            return str(partials_path / "vega_lite_chart.html")

        # if (
        #     interface.kind
        #     in [
        #         InterfaceKindChoices.BOOL,
        #         InterfaceKindChoices.FLOAT,
        #         InterfaceKindChoices.INTEGER,
        #         InterfaceKindChoices.STRING,
        #     ]
        #     and interface.store_in_database
        # ):
        #     return str(partials_path / "json_preview.html")

        return str(partials_path / "json.html")

    if interface.super_kind == InterfaceSuperKindChoices.FILE:
        if interface.kind in (
            InterfaceKindChoices.THUMBNAIL_JPG,
            InterfaceKindChoices.THUMBNAIL_PNG,
        ):
            return str(partials_path / "thumbnail.html")

        return str(partials_path / "file.html")

    if interface.super_kind == InterfaceSuperKindChoices.IMAGE:
        return str(partials_path / "image.html")

    return str(partials_path / "fallback.html")
