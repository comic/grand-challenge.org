from urllib.parse import urljoin

from django.conf import settings
from django.core.urlresolvers import reverse as reverse_org


def reverse(viewname, urlconf=None, args=None, kwargs=None, prefix=None,
            current_app=None):
    """ Reverse url, but try to use subdomain to designate site where possible.
    This means 'site1' will not get url 'hostname/site/site1' but rather 'projectname.hostname'
    """

    if args is not None:
        challenge_short_name = args[0]
    elif kwargs is not None and 'challenge_short_name' in kwargs:
        challenge_short_name = kwargs['challenge_short_name']
    else:
        challenge_short_name = None

    if settings.SUBDOMAIN_IS_PROJECTNAME and challenge_short_name:
        protocol, domainname = settings.MAIN_HOST_NAME.split("//")
        base_url = f"{protocol}//{challenge_short_name}.{domainname}".lower()

        site_url = reverse_org('challenge-homepage',
                               args=[challenge_short_name]).lower()
        target_url = reverse_org(viewname, urlconf, args, kwargs, prefix,
                                 current_app).lower()

        if target_url.startswith(site_url):
            target_url = target_url.replace(site_url, "/")

        return urljoin(base_url, target_url)

    else:
        return reverse_org(viewname, urlconf, args, kwargs, prefix,
                           current_app)
