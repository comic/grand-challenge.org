from urllib import parse

from django import template
from django.conf import settings

from grandchallenge.workstations.models import Session

register = template.Library()


def update_url(*, url: str, query: dict) -> str:
    """
    Updates a url with new params. If the url contains a fragment then the
    params will be added to the fragment, otherwise they will be added to
    the query.
    """

    url_parts = list(parse.urlparse(url))

    # If a fragment exists, update the fragment, else update the query
    idx = 5 if url_parts[5] else 4

    old_query = parse.parse_qs(url_parts[idx])
    old_query.update(query)
    url_parts[idx] = parse.unquote(parse.urlencode(old_query, doseq=True))

    return parse.urlunparse(url_parts)


@register.simple_tag(takes_context=True)
def workstation_url(context, image, overlay=None):
    """ Generate a url to view this image and overlay in a workstation """

    user = context.request.user
    session = (
        Session.objects.filter(creator=user)
        .exclude(status__in=[Session.QUEUED, Session.STOPPED])
        .order_by("-created")
        .first()
    )

    if session:
        url = session.workstation_url
    else:
        url = settings.CIRRUS_APPLICATION

    query = {settings.CIRRUS_BASE_IMAGE_QUERY_PARAM: image.pk}
    if overlay is not None:
        query.update({settings.CIRRUS_ANNOTATION_QUERY_PARAM: overlay.pk})

    return update_url(url=url, query=query)
