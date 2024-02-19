from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import (
    get_next_redirect_url,
    user_email,
    user_username,
)
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialLogin
from allauth_2fa.utils import user_has_valid_totp_device
from django import forms
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme, urlencode

from grandchallenge.challenges.models import Challenge
from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.subdomains.utils import reverse


class AccountAdapter(DefaultAccountAdapter):
    def has_2fa_enabled(self, user):
        """Returns True if the user has 2FA configured."""
        return user_has_valid_totp_device(user)

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

    def pre_login(self, request, user, **kwargs):
        # this is copied from the a pending PR on django-allauth-2fa repo:
        # https://github.com/valohai/django-allauth-2fa/pull/131

        response = super().pre_login(request, user, **kwargs)
        if response:
            return response

        # Require two-factor authentication if it has been configured
        if self.has_2fa_enabled(user):
            self.stash_pending_login(request, user, **kwargs)
            redirect_url = reverse("two-factor-authenticate")
            query_params = request.GET.copy()
            next_url = get_next_redirect_url(request)
            if next_url:
                query_params["next"] = next_url
            if query_params:
                redirect_url += "?" + urlencode(query_params)
            raise ImmediateHttpResponse(
                response=HttpResponseRedirect(redirect_url)
            )

    def stash_pending_login(self, request, user, **kwargs):
        # this is copied from the a pending PR on django-allauth-2fa repo:
        # https://github.com/valohai/django-allauth-2fa/pull/131

        # Cast to string for the case when this is not a JSON serializable
        # object, e.g. a UUID.
        request.session["allauth_2fa_user_id"] = str(user.id)
        login_kwargs = kwargs.copy()
        signal_kwargs = login_kwargs.get("signal_kwargs")
        if signal_kwargs:
            sociallogin = signal_kwargs.get("sociallogin")
            if sociallogin:
                signal_kwargs = signal_kwargs.copy()
                signal_kwargs["sociallogin"] = sociallogin.serialize()
                login_kwargs["signal_kwargs"] = signal_kwargs
        request.session["allauth_2fa_login"] = login_kwargs

    def unstash_pending_login_kwargs(self, request):
        # this is copied from the a pending PR on django-allauth-2fa repo:
        # https://github.com/valohai/django-allauth-2fa/pull/131

        login_kwargs = request.session.pop("allauth_2fa_login", None)
        if login_kwargs is None:
            raise PermissionDenied()
        signal_kwargs = login_kwargs.get("signal_kwargs")
        if signal_kwargs:
            sociallogin = signal_kwargs.get("sociallogin")
            if sociallogin:
                signal_kwargs["sociallogin"] = SocialLogin.deserialize(
                    sociallogin
                )
        return login_kwargs

    def post_login(self, request, user, **kwargs):
        response = super().post_login(request, user, **kwargs)
        if user.is_staff or user.is_superuser:
            send_standard_email_batch(
                subject="Security Alert",
                message="<p>We noticed a new login to your account. If this was you, you don't need to do anything. If not, please change your password and update your 2FA device.</p>",
                recipients=[user],
            )
        return response


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, *args, **kwargs):
        user = super().populate_user(*args, **kwargs)

        if not user_username(user) and user_email(user):
            # If no username set, use the first part of their email
            user_username(user, user_email(user).split("@")[0])

        return user
