from django import template
from django.conf import settings
from django.utils.http import urlencode

register = template.Library()


@register.simple_tag()
def workstation_query(image=None, overlay=None, reader_study=None):
    """
    Generate the workstation query string for this image with overlay or
    reader_study.
    """

    if image is not None:
        query = {settings.WORKSTATIONS_BASE_IMAGE_QUERY_PARAM: image.pk}
        if overlay is not None:
            query.update(
                {settings.WORKSTATIONS_OVERLAY_QUERY_PARAM: overlay.pk}
            )
    elif reader_study is not None:
        query = {
            settings.WORKSTATIONS_READY_STUDY_QUERY_PARAM: reader_study.pk
        }
    else:
        query = {}

    return urlencode(query)
