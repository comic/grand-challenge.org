import json

from grandchallenge.components.models import InterfaceKindChoices
from grandchallenge.core.validators import JSONValidator
from grandchallenge.hanging_protocols.models import (
    VIEW_CONTENT_SCHEMA,
    ViewportNames,
)


def generate_view_content_example(interfaces):
    images = list(
        interfaces.filter(kind=InterfaceKindChoices.IMAGE)
        .order_by("slug")
        .values_list("slug", flat=True)
    )
    overlays = list(
        interfaces.filter(
            kind__in=[
                InterfaceKindChoices.SEGMENTATION,
                InterfaceKindChoices.HEAT_MAP,
                InterfaceKindChoices.DISPLACEMENT_FIELD,
            ]
        )
        .order_by("slug")
        .values_list("slug", flat=True)
    )
    view_content_example = {}

    for port in ViewportNames.values:
        if len(images) == 0:
            break

        view_content_example[port] = [images.pop(0)]
        if len(overlays) > 0:
            view_content_example[port].append(overlays.pop(0))

    JSONValidator(schema=VIEW_CONTENT_SCHEMA)(value=view_content_example)

    return json.dumps(view_content_example) if view_content_example else None
