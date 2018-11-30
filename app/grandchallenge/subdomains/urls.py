from urllib.parse import urljoin

from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse as reverse_org


def reverse(viewname, urlconf=None, args=None, kwargs=None, current_app=None):
    """ Reverse url, but try to use subdomain to designate site where possible.
    This means 'site1' will not get url 'hostname/site/site1' but rather
    'challenge.hostname'
    """
    kwargs = kwargs or {}

    domain = Site.objects.get_current().domain.lower()
    scheme = "http"

    if settings.SUBDOMAIN_IS_PROJECTNAME and "challenge_short_name" in kwargs:
        challenge_short_name = kwargs.pop("challenge_short_name")
        domain = f"{scheme}://{challenge_short_name}.{domain}"
        urlconf = urlconf or "grandchallenge.core.urls"
    else:
        domain = f"{scheme}://{domain}"
        urlconf = urlconf or settings.ROOT_URLCONF

    path = reverse_org(
        viewname,
        urlconf=urlconf,
        args=args,
        kwargs=kwargs,
        current_app=current_app,
    )

    return urljoin(domain, path)
