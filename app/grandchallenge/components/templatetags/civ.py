from django import template
from django.db import models

from grandchallenge.components.models import InterfaceKindChoices

register = template.Library()


@register.filter
def sort_civs(civs):

    # Allows for X.outputs (ommiting the .all)
    iterable = (
        civs.all() if isinstance(civs, models.manager.BaseManager) else civs
    )

    values = []
    charts = []
    thumbnails = []
    images = []
    files = []
    residual = []

    for v in sorted(list(iterable), key=lambda civ: civ.interface.slug):
        if v.interface.is_json_kind:
            if v.interface.kind == InterfaceKindChoices.CHART:
                charts.append(v)
            else:
                values.append(v)
        elif v.interface.is_file_kind:
            if v.interface.is_thumbnail_kind:
                thumbnails.append(v)
            else:
                files.append(v)
        elif v.interface.is_image_kind:
            images.append(v)
        else:
            residual.append(v)

    return [*values, *thumbnails, *charts, *files, *images, *residual]
