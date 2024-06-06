from collections.abc import Iterable

from django import template

from grandchallenge.components.models import (
    ComponentInterfaceValue,
    InterfaceKindChoices,
)

register = template.Library()


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


@register.filter
def can_preview(component_interface_value):
    return component_interface_value.interface.kind in [
        InterfaceKindChoices.BOOL,
        InterfaceKindChoices.FLOAT,
        InterfaceKindChoices.INTEGER,
        InterfaceKindChoices.STRING,
    ]


@register.filter
def is_thumbnail_kind(component_interface_value):
    return component_interface_value.interface.kind in [
        InterfaceKindChoices.THUMBNAIL_JPG,
        InterfaceKindChoices.THUMBNAIL_PNG,
    ]
