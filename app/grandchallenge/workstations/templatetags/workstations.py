from django import template
from django.conf import settings
from django.utils.http import urlencode

register = template.Library()


@register.simple_tag()
def workstation_query(
    image=None, overlay=None, reader_study=None, config=None
):
    """
    Generate the workstation query string.

    Supports setting the image with overlay or a reader_study.
    """
    if image:
        query = {
            settings.WORKSTATIONS_BASE_IMAGE_QUERY_PARAM: getattr(
                image, "pk", image
            )
        }
        if overlay:
            query.update(
                {
                    settings.WORKSTATIONS_OVERLAY_QUERY_PARAM: getattr(
                        overlay, "pk", overlay
                    )
                }
            )
    elif reader_study:
        query = {
            settings.WORKSTATIONS_READY_STUDY_QUERY_PARAM: reader_study.pk
        }
    else:
        query = {}

    if config:
        # Explicit configs have precedence
        query.update(
            {
                settings.WORKSTATIONS_CONFIG_QUERY_PARAM: getattr(
                    config, "pk", config
                )
            }
        )
    elif reader_study and reader_study.workstation_config:
        query.update(
            {
                settings.WORKSTATIONS_CONFIG_QUERY_PARAM: reader_study.workstation_config.pk
            }
        )

    return urlencode(query)
