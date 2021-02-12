from allauth.account.adapter import DefaultAccountAdapter
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
            allowed_hosts={*challenge_domains, *workstation_domains},
            require_https=True,
        )

    def clean_email(self, email):
        email = super().clean_email(email=email)

        domain = email.split("@")[1].lower()

        if domain in settings.DISALLOWED_EMAIL_DOMAINS:
            raise forms.ValidationError(
                f"Email addresses hosted by {domain} cannot be used."
            )

        return email
