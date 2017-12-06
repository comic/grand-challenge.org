from django.core.urlresolvers import reverse as reverse_org

from comicsite.utils import uri_to_url


def reverse(viewname, urlconf=None, args=None, kwargs=None, prefix=None, current_app=None):
    """ Reverse url, but try to use subdomain to designate site where possible.
    This means 'site1' will not get url 'hostname/site/site1' but rather 'projectname.hostname'
    """

    uri = reverse_org(viewname, urlconf, args, kwargs, prefix, current_app)
    url = uri_to_url(uri)

    return url
