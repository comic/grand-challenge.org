from django import template
from django.conf import settings
from django.utils.http import urlencode

from grandchallenge.subdomains.utils import reverse

register = template.Library()


def get_workstation_query_string(  # noqa: C901
    image=None,
    overlay=None,
    reader_study=None,
    algorithm_job=None,
    archive_item=None,
    config=None,
    user=None,
    display_set=None,
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
    elif display_set:
        query = {settings.WORKSTATIONS_DISPLAY_SET_QUERY_PARAM: display_set.pk}
    elif reader_study:
        query = {
            settings.WORKSTATIONS_READY_STUDY_QUERY_PARAM: reader_study.pk
        }
        if user:
            query.update(
                {settings.WORKSTATIONS_USER_QUERY_PARAM: user.username}
            )
    elif algorithm_job:
        query = {
            settings.WORKSTATIONS_ALGORITHM_JOB_QUERY_PARAM: algorithm_job.pk
        }
    elif archive_item:
        query = {
            settings.WORKSTATIONS_ARCHIVE_ITEM_QUERY_PARAM: archive_item.pk
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
    elif display_set and display_set.reader_study.workstation_config:
        query.update(
            {
                settings.WORKSTATIONS_CONFIG_QUERY_PARAM: display_set.reader_study.workstation_config.pk
            }
        )

    return urlencode(query)


@register.simple_tag()
def workstation_query(**kwargs):
    return get_workstation_query_string(**kwargs)


@register.simple_tag()
def workstation_session_control_data(
    workstation=None, context_object=None, timeout=None, **kwargs
):
    create_session_url = reverse(
        "workstations:workstation-session-create",
        kwargs={"slug": workstation.slug},
    )
    workstation_query_string = get_workstation_query_string(**kwargs)
    window_identifier = f"workstation-{context_object._meta.app_label}"
    return (
        f"data-session-control "
        f"data-create-session-url= {create_session_url} "
        f"data-workstation-query= {workstation_query_string} "
        f"data-workstation-window-identifier= {window_identifier} "
        f"data-timeout= {timeout if timeout else ''}"
    )
