from urllib.parse import urljoin

from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse as reverse_org
from django.utils.functional import lazy


def reverse(viewname, urlconf=None, args=None, kwargs=None, current_app=None):
    """Reverse lookup for the viewname taking into account subdomains."""
    kwargs = kwargs or {}

    scheme = settings.DEFAULT_SCHEME

    host = Site.objects.get_current().domain.lower()
    domain = f"{scheme}://{host}"

    if "challenge_short_name" in kwargs:
        challenge_short_name = kwargs.pop("challenge_short_name")
        domain = f"{scheme}://{challenge_short_name}.{host}"
        urlconf = urlconf or settings.SUBDOMAIN_URL_CONF
    else:
        urlconf = urlconf or settings.ROOT_URLCONF

    path = reverse_org(
        viewname,
        urlconf=urlconf,
        args=args,
        kwargs=kwargs,
        current_app=current_app,
    )

    return urljoin(domain.lower(), path)


reverse_lazy = lazy(reverse, str)
