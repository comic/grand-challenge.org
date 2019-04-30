from django import template
from django.conf import settings

register = template.Library()


def workstation_query(image, overlay=None):
    """ Generate the workstation query string for this image and overlay """
    query = {settings.WORKSTATIONS_BASE_IMAGE_QUERY_PARAM: image.pk}

    if overlay is not None:
        query.update({settings.WORKSTATIONS_OVERLAY_QUERY_PARAM: overlay.pk})

    return "&".join([f"{k}={v}" for k, v in query.items()])
