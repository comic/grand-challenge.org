import logging

from django.conf import settings
from guardian.shortcuts import get_perms
from guardian.utils import get_anonymous_user

from grandchallenge.policies.models import Policy

logger = logging.getLogger(__name__)


def challenge(request):
    try:
        challenge = request.challenge

        if challenge is None:
            return {}

    except AttributeError:
        logger.warning(f"Could not get challenge for request: {request}")
        return {}

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


def debug(*_, **__):
    return {"DEBUG": settings.DEBUG}


def sentry_dsn(*_, **__):
    return {
        "SENTRY_DSN": settings.SENTRY_DSN,
        "SENTRY_ENABLE_JS_REPORTING": settings.SENTRY_ENABLE_JS_REPORTING,
    }


def policy_pages(*_, **__):
    return {"policy_pages": Policy.objects.all()}
