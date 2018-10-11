from urllib.parse import urljoin

from django.conf import settings
from django.urls import reverse as reverse_org


def reverse(viewname, urlconf=None, args=None, kwargs=None, current_app=None):
    """ Reverse url, but try to use subdomain to designate site where possible.
    This means 'site1' will not get url 'hostname/site/site1' but rather
    'challenge.hostname'
    """
    args = args or []
    kwargs = kwargs or {}

    if settings.SUBDOMAIN_IS_PROJECTNAME:

        if args:
            challenge_short_name = args[0]
        else:
            challenge_short_name = kwargs.get(
                "challenge_short_name", settings.MAIN_PROJECT_NAME
            )

        protocol, domainname = settings.MAIN_HOST_NAME.split("//")

        if challenge_short_name.lower() == settings.MAIN_PROJECT_NAME.lower():
            base_url = f"{protocol}//{domainname}"
        else:
            base_url = f"{protocol}//{challenge_short_name}.{domainname}"

        site_url = reverse_org(
            "challenge-homepage", args=[challenge_short_name]
        )

        target_url = reverse_org(
            viewname,
            urlconf=urlconf,
            args=args,
            kwargs=kwargs,
            current_app=current_app,
        )

        if target_url.startswith(site_url):
            target_url = target_url.replace(site_url, "/")

        return urljoin(base_url.lower(), target_url)

    else:

        return reverse_org(
            viewname,
            urlconf=urlconf,
            args=args,
            kwargs=kwargs,
            current_app=current_app,
        )
