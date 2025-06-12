import logging
import re

from django.conf import settings
from django.shortcuts import get_object_or_404, redirect

from grandchallenge.challenges.models import Challenge
from grandchallenge.subdomains.utils import reverse

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
        Adds the challenge to the request based on the subdomain,
        raising Http404 if challenge is not valid. Requires the
        subdomain to be set on the request (eg, by using subdomain_middleware)
        """
        subdomain = request.subdomain

        if subdomain in [*settings.WORKSTATIONS_RENDERING_SUBDOMAINS, None]:
            request.challenge = None
        else:
            request.challenge = get_object_or_404(
                Challenge.objects.with_available_compute()
                .select_related("discussion_forum")
                .prefetch_related("phase_set"),
                short_name__iexact=subdomain,
            )

            if request.challenge.is_suspended:
                return redirect(reverse("challenge-suspended"))

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
