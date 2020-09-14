import logging
import re

from django.conf import settings
from django.http import HttpResponseRedirect

from grandchallenge.challenges.models import Challenge

logger = logging.getLogger(__name__)


def subdomain_middleware(get_response):
    def middleware(request):
        """Adds the subdomain to the request."""
        host = request.get_host().lower()
        domain = request.site.domain.lower()

        pattern = rf"^(?:(?P<subdomain>.*?)[.])?{domain}$"
        matches = re.match(pattern, host)

        try:
            request.subdomain = matches.group("subdomain")
        except AttributeError:
            # The request was not made on this domain
            request.subdomain = None

        response = get_response(request)

        return response

    return middleware


def challenge_subdomain_middleware(get_response):
    def middleware(request):
        """
        Adds the challenge to the request based on the subdomain, redirecting
        to the main site if the challenge is not valid. Requires the
        subdomain to be set on the request (eg, by using subdomain_middleware)
        """
        subdomain = request.subdomain

        if subdomain in [*settings.WORKSTATIONS_RENDERING_SUBDOMAINS, None]:
            request.challenge = None
        else:
            try:
                request.challenge = (
                    Challenge.objects.select_related("forum")
                    .prefetch_related("phase_set")
                    .get(short_name__iexact=subdomain)
                )
            except Challenge.DoesNotExist:
                logger.warning(f"Could not find challenge {subdomain}")
                domain = request.site.domain.lower()
                return HttpResponseRedirect(f"{request.scheme}://{domain}/")

        response = get_response(request)

        return response

    return middleware


def subdomain_urlconf_middleware(get_response):
    def middleware(request):
        """
        Adds the urlconf to the middleware based on the challenge associated
        with this request, ensures that the correct urls are matched by the
        request
        """
        if request.challenge:
            request.urlconf = settings.CHALLENGE_SUBDOMAIN_URL_CONF
        elif request.subdomain in settings.WORKSTATIONS_RENDERING_SUBDOMAINS:
            request.urlconf = settings.RENDERING_SUBDOMAIN_URL_CONF
        else:
            request.urlconf = settings.ROOT_URLCONF

        response = get_response(request)

        return response

    return middleware
