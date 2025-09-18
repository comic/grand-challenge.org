import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_email, user_username
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden
from django.template import loader
from django.utils.http import url_has_allowed_host_and_scheme

from grandchallenge.challenges.models import Challenge
from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.profiles.models import EmailSubscriptionTypes
from grandchallenge.verifications.models import clean_email

logger = logging.getLogger(__name__)


class AccountAdapter(DefaultAccountAdapter):
    def is_safe_url(self, url):
        challenge_domains = {
            f"{c.short_name.lower()}{settings.SESSION_COOKIE_DOMAIN}"
            for c in Challenge.objects.all()
        }
        workstation_domains = {
            f"{r}{settings.SESSION_COOKIE_DOMAIN}"
            for r in settings.WORKSTATIONS_ACTIVE_REGIONS
        }

        return url_has_allowed_host_and_scheme(
            url=url,
            allowed_hosts={
                *challenge_domains,
                *workstation_domains,
                settings.SESSION_COOKIE_DOMAIN.lstrip("."),
            },
        )

    @property
    def _is_password_reset_request(self):
        return (
            self.request.resolver_match.namespace == ""
            and self.request.resolver_match.url_name
            == "account_reset_password"
        )

    def clean_email(self, email):
        email = super().clean_email(email=email)

        if self._is_password_reset_request:
            # Allauths cleaning is sufficient for password reset
            return email
        else:
            # Checks for banned domains and existing emails across the site
            return clean_email(email=email)

    def post_login(self, request, user, **kwargs):
        response = super().post_login(request, user, **kwargs)
        site = Site.objects.get_current()
        if user.is_staff or user.is_superuser:
            send_standard_email_batch(
                site=site,
                subject="Security Alert",
                markdown_message="We noticed a new login to your account. If this was you, you don't need to do anything. If not, please change your password and update your 2FA device.",
                recipients=[user],
                subscription_type=EmailSubscriptionTypes.SYSTEM,
            )
        return response


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        email = sociallogin.account.extra_data.get("email")

        try:
            clean_email(email=email)
        except ValidationError as error:
            logger.info(f"Social signup disallowed: {error.message}")
            raise ImmediateHttpResponse(
                HttpResponseForbidden(
                    loader.get_template("403.html").render(
                        request=request, context={"reason": str(error.message)}
                    )
                )
            )

        return super().is_open_for_signup(request, sociallogin)

    def populate_user(self, *args, **kwargs):
        user = super().populate_user(*args, **kwargs)

        if not user_username(user) and user_email(user):
            # If no username set, use the first part of their email
            user_username(user, user_email(user).split("@")[0])

        return user
