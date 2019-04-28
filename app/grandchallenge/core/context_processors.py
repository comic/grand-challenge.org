import logging

from django.conf import settings
from guardian.shortcuts import get_perms
from guardian.utils import get_anonymous_user

logger = logging.getLogger(__name__)


def challenge(request):
    try:
        challenge = request.challenge
    except AttributeError:
        challenge = None

        # build_absolute_uri does not exist in some cases (eg, in tests)
        try:
            warning_url = request.build_absolute_url()
        except AttributeError:
            warning_url = request.path

        logger.warning(f"Could not get challenge for request: {warning_url}")

    if challenge is None:
        return {}
    else:
        try:
            user = request.user
        except AttributeError:
            user = get_anonymous_user()

        return {
            "challenge": challenge,
            "challenge_perms": get_perms(user, challenge),
            "user_is_participant": challenge.is_participant(user),
            "pages": challenge.page_set.all(),
        }


def google_keys(*_, **__):
    return {
        "google_analytics_id": settings.GOOGLE_ANALYTICS_ID,
        "geochart_api_key": settings.GOOGLE_MAPS_API_KEY,
    }
