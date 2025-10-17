from typing import NamedTuple

from django import template
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.http import urlencode

from grandchallenge.subdomains.utils import reverse

register = template.Library()


class PathAndQueryString(NamedTuple):
    path: str
    query_string: str


def get_workstation_path_and_query_string(
    image=None,
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
        path = f"{settings.WORKSTATIONS_BASE_IMAGE_PATH_PARAM}/{getattr(image, 'pk', image)}"
    elif display_set:
        path = (
            f"{settings.WORKSTATIONS_DISPLAY_SET_PATH_PARAM}/{display_set.pk}"
        )
    elif reader_study:
        path = (
            f"{settings.WORKSTATIONS_READY_STUDY_PATH_PARAM}/{reader_study.pk}"
        )
    elif algorithm_job:
        path = f"{settings.WORKSTATIONS_ALGORITHM_JOB_PATH_PARAM}/{algorithm_job.pk}"
    elif archive_item:
        path = f"{settings.WORKSTATIONS_ARCHIVE_ITEM_PATH_PARAM}/{archive_item.pk}"
    else:
        path = ""

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
    if reader_study and user:
        query.update({settings.WORKSTATIONS_USER_QUERY_PARAM: user.username})

    return PathAndQueryString(path, urlencode(query))


@register.simple_tag()
def workstation_session_control_data(
    *, workstation, context_object, timeout=False, **kwargs
):
    if workstation:
        create_session_url = reverse(
            "workstations:workstation-session-create",
            kwargs={"slug": workstation.slug},
        )
    else:
        create_session_url = reverse(
            "workstations:default-session-create",
        )

    pqs = get_workstation_path_and_query_string(**kwargs)
    window_identifier = f"workstation-{context_object._meta.app_label}"
    data_attrs = {
        "data-session-control": True,
        "data-create-session-url": create_session_url,
        "data-workstation-path": pqs.path,
        "data-workstation-query": pqs.query_string,
        "data-workstation-window-identifier": window_identifier,
        "data-timeout": timeout,
    }
    return render_to_string(
        "django/forms/widgets/attrs.html", {"widget": {"attrs": data_attrs}}
    )
