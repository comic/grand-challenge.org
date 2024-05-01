from allauth import app_settings
from allauth.account.adapter import get_adapter
from allauth.mfa.utils import is_mfa_enabled
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin

from grandchallenge.core.utils.list_url_names import list_url_names
from grandchallenge.subdomains.utils import reverse


class RequireStaffAndSuperuser2FAMiddleware(MiddlewareMixin):
    """Force multi-factor authentication for staff users and superusers."""

    allowed_urls = list_url_names("allauth.account.urls")

    def mfa_required(self, request):
        return request.user.is_staff or request.user.is_superuser

    def redirect_to_mfa_setup(self, request):
        adapter = get_adapter(request)
        adapter.add_message(
            request, messages.ERROR, "allauth/mfa/require_mfa.txt"
        )
        return HttpResponseRedirect(reverse("mfa_activate_totp"))

    def process_view(self, request, view_func, view_args, view_kwargs):
        # If MFA is not enabled, do nothing
        if not app_settings.MFA_ENABLED:
            return None

        # If the user is not authenticated, do nothing
        if not request.user.is_authenticated:
            return None

        # If we are on an allowed page, do nothing
        if request.resolver_match.url_name in self.allowed_urls:
            return None

        # If this request does not require MFA, do nothing
        if not self.mfa_required(request):
            return None

        # If the user has MFA enabled already, do nothing
        if is_mfa_enabled(request.user):
            return None

        return self.redirect_to_mfa_setup(request)
