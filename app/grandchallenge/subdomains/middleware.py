import re

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponseRedirect

from grandchallenge.challenges.models import Challenge


def subdomain_middleware(get_response):
    def middleware(request):
        """ Adds the subdomain to the request """
        host = request.get_host().lower()
        domain = get_current_site(request).domain.lower()

        pattern = f"^(?:(?P<subdomain>.*?)\.)?{domain}$"
        matches = re.match(pattern, host)

        request.subdomain = matches.group("subdomain")

        response = get_response(request)

        return response

    return middleware


def challenge_subdomain_middleware(get_response):
    def middleware(request):
        """
        Adds the challenge to the request based on the subdomain, redirecting
        to the main site if the challenge is not valid
        """

        if request.subdomain is None:
            request.challenge = Challenge.objects.get(
                short_name__iexact=settings.MAIN_PROJECT_NAME
            )
        else:
            try:
                request.challenge = Challenge.objects.get(
                    short_name__iexact=request.subdomain
                )
            except Challenge.DoesNotExist:
                domain = get_current_site(request).domain.lower()
                return HttpResponseRedirect(f"{request.scheme}://{domain}/")

        response = get_response(request)

        return response

    return middleware
