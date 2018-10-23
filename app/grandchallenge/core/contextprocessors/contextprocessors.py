"""
 Custom processors to pass variables to views rendering template tags 
 see http://www.djangobook.com/en/2.0/chapter09.html  
"""
from django.conf import settings
from django.http import Http404
from django.urls import resolve
from guardian.shortcuts import get_perms

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.utils import build_absolute_uri


def comic_site(request):
    """ Find out in which challenge this request is for. If you cannot
    figure it out. Use main project. 
    
    """
    try:
        resolution = resolve(request.path)
    except Http404 as e:
        # fail silently beacuse any exeception here will cause a 500 server error
        # on page. Let views show errors but not the context processor
        resolution = resolve("/")

    challenge_short_name = resolution.kwargs.get(
        "challenge_short_name", settings.MAIN_PROJECT_NAME
    )

    try:
        challenge = Challenge.objects.get(
            short_name__iexact=challenge_short_name
        )
        pages = challenge.page_set.all()
    except Challenge.DoesNotExist:
        # Don't crash the system here, if a challenge cannot be found it will crash
        # in a more appropriate location
        return {}

    return {
        "site": challenge,
        "challenge_perms": get_perms(request.user, challenge),
        "user_is_participant": challenge.is_participant(request.user),
        "pages": pages,
        "main_challenge_name": settings.MAIN_PROJECT_NAME,
    }


def subdomain_absolute_uri(request):
    uri = build_absolute_uri(request)
    return {"subdomain_absolute_uri": uri}


def google_analytics_id(*_, **__):
    return {"google_analytics_id": settings.GOOGLE_ANALYTICS_ID}
