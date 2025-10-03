import logging

from django.conf import settings
from django.utils.safestring import mark_safe
from guardian.shortcuts import get_perms
from guardian.utils import get_anonymous_user

from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.hanging_protocols.models import ViewportNames
from grandchallenge.participants.models import RegistrationRequest
from grandchallenge.policies.models import Policy
from grandchallenge.profiles.forms import NewsletterSignupForm

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
        "pending_requests": challenge.registrationrequest_set.filter(
            status=RegistrationRequest.PENDING
        ),
        "onboardingtask_aggregates": challenge.onboarding_tasks.updatable_by(
            user
        )
        .with_overdue_status()
        .status_aggregates,
        "invoice_aggregates": challenge.invoices.with_overdue_status().status_aggregates,
    }


def django_settings(*_, **__):
    return {
        "COMMIT_ID": settings.COMMIT_ID,
        "SUPPORT_EMAIL": mark_safe(random_encode(settings.SUPPORT_EMAIL)),
        "DEBUG": settings.DEBUG,
        "ACTSTREAM_ENABLE": settings.ACTSTREAM_ENABLE,
    }


def sentry_dsn(request):
    return {
        "SENTRY_DSN": settings.SENTRY_DSN,
        "SENTRY_ENABLE_JS_REPORTING": request.path.endswith("/create/")
        and settings.SENTRY_ENABLE_JS_REPORTING,
    }


def footer_links(*_, **__):
    return {"policy_pages": Policy.objects.all()}


def about_page(*_, **__):
    return {"about_page_url": settings.FLATPAGE_ABOUT_URL}


def newsletter_signup(*_, **__):
    return {"newletter_signup_form": NewsletterSignupForm}


def viewport_names(*_, **__):
    return {"viewport_names": ViewportNames.values}


def workstation_domains(*_, **__):
    return {
        "workstation_domains": [
            *[
                f"https://{region}{settings.SESSION_COOKIE_DOMAIN}"
                for region in settings.WORKSTATIONS_ACTIVE_REGIONS
            ],
            *settings.WORKSTATIONS_EXTRA_BROADCAST_DOMAINS,
        ]
    }
