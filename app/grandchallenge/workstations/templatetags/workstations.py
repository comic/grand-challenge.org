from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

from django import template
from django.conf import settings

from grandchallenge.workstations.models import Session

register = template.Library()


@register.simple_tag(takes_context=True)
def workstation_link(context, image):
    user = context.request.user
    session = (
        Session.objects.filter(creator=user)
        .exclude(status__in=[Session.QUEUED, Session.STOPPED])
        .order_by("-created")
        .first()
    )

    if session:
        url = urljoin(
            session.get_absolute_url(), session.workstation_image.initial_path
        )
    else:
        url = settings.CIRRUS_APPLICATION

    url_parts = list(urlparse(url))
    query = parse_qs(url_parts[4])
    query.update(parse_qs(image.query_string))
    url_parts[4] = urlencode(query, doseq=True)

    return f"{urlunparse(url_parts)}"
