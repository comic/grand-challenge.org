from django import template

from grandchallenge.components.models import (
    ComponentInterfaceValue,
    InterfaceKindChoices,
    InterfaceSuperKindChoices,
)

register = template.Library()


@register.filter
def is_thumbnail(civ: ComponentInterfaceValue):
    return (
        civ.interface.kind
        in (
            InterfaceKindChoices.THUMBNAIL_JPG,
            InterfaceKindChoices.THUMBNAIL_PNG,
        )
        and civ.interface.super_kind == InterfaceSuperKindChoices.value
    )


@register.filter
def is_chart(civ: ComponentInterfaceValue):
    return (
        civ.interface.kind == InterfaceKindChoices.CHART
        and civ.interface.super_kind == InterfaceSuperKindChoices.value
    )
