import logging

from django.conf import settings
from guardian.shortcuts import get_perms
from guardian.utils import get_anonymous_user

from grandchallenge.challenges.models import Challenge

logger = logging.getLogger(__name__)


def comic_site(request):
    try:
        challenge = request.challenge
    except AttributeError:

        # build_absolute_uri does not exist in some cases (eg, in tests)
        try:
            warning_url = request.build_absolute_url()
        except AttributeError:
            warning_url = request.path

        logger.warning(f"Could not get challenge for request: {warning_url}")
        challenge = None

    if challenge is None:
        # Use the main challenge if there is no challenge associated with
        # this request
        challenge = Challenge.objects.get(
            short_name__iexact=settings.MAIN_PROJECT_NAME
        )

    try:
        user = request.user
    except AttributeError:
        user = get_anonymous_user()

    permissions = get_perms(user, challenge)
    pages = challenge.page_set.all()
    is_participant = challenge.is_participant(user)

    return {
        "site": challenge,
        "challenge_perms": permissions,
        "user_is_participant": is_participant,
        "pages": pages,
        "main_challenge_name": settings.MAIN_PROJECT_NAME,
        "geochart_api_key": settings.GOOGLE_MAPS_API_KEY,
    }


def google_analytics_id(*_, **__):
    return {"google_analytics_id": settings.GOOGLE_ANALYTICS_ID}
