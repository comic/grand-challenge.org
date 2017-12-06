import re

from django.conf import settings


def build_absolute_uri(request):
    """
    Total hack to get around SUBDOMAN_IS_PROJECTNAME for absolute urls
    """
    return uri_to_url(request.build_absolute_uri())


def uri_to_url(uri):
    if settings.SUBDOMAIN_IS_PROJECTNAME:
        try:
            m = re.search(
                r'\/\/(?P<host>[^\/]+)\/site\/(?P<subdomain>[^\/]+)\/',
                uri + '/')
            host = m['host']
            subdomain = m['subdomain']
            uri = uri[:m.start(0)] \
                  + '//' \
                  + subdomain \
                  + '.' \
                  + host \
                  + '/' \
                  + uri[m.end(0):]
        except TypeError:
            # nothing to rewrite
            pass

    return uri
