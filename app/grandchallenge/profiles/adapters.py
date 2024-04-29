from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_email, user_username
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django import forms
from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.http import url_has_allowed_host_and_scheme

from grandchallenge.challenges.models import Challenge
from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.profiles.models import EmailSubscriptionTypes


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

    def clean_email(self, email):
        email = super().clean_email(email=email)

        domain = email.split("@")[1].lower()

        if domain in settings.DISALLOWED_EMAIL_DOMAINS:
            raise forms.ValidationError(
                f"Email addresses hosted by {domain} cannot be used."
            )

        return email

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
    def populate_user(self, *args, **kwargs):
        user = super().populate_user(*args, **kwargs)

        if not user_username(user) and user_email(user):
            # If no username set, use the first part of their email
            user_username(user, user_email(user).split("@")[0])

        return user
