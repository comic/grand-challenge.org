from allauth.account.utils import user_email, user_username
from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth_2fa.adapter import OTPAdapter
from allauth_2fa.utils import user_has_valid_totp_device
from django import forms
from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme

from grandchallenge.challenges.models import Challenge
from grandchallenge.subdomains.utils import reverse


class AccountAdapter(OTPAdapter):
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

    def pre_social_login(self, request, sociallogin):
        if user_has_valid_totp_device(sociallogin.user):
            # Cast to string for the case when this is not a JSON serializable
            # object, e.g. a UUID.
            request.session["allauth_2fa_user_id"] = str(sociallogin.user.id)
            redirect_url = reverse("two-factor-authenticate")
            redirect_url += "?next=" + request.get_full_path()
            raise ImmediateHttpResponse(
                response=HttpResponseRedirect(redirect_url)
            )
        elif sociallogin.user.is_staff and not user_has_valid_totp_device(
            sociallogin.user
        ):
            redirect_url = reverse("two-factor-setup")
            redirect_url += "?next=" + request.get_full_path()
            raise ImmediateHttpResponse(
                response=HttpResponseRedirect(redirect_url)
            )
        return super().pre_social_login(request, sociallogin)
