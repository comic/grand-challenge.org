from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_email, user_username
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django import forms
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme

from grandchallenge.challenges.models import Challenge


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


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, *args, **kwargs):
        user = super().populate_user(*args, **kwargs)

        if not user_username(user) and user_email(user):
            # If no username set, use the first part of their email
            user_username(user, user_email(user).split("@")[0])

        return user
