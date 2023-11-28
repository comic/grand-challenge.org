from allauth_2fa.middleware import BaseRequire2FAMiddleware
from django.urls import Resolver404, get_resolver
from django.utils.deprecation import MiddlewareMixin


class RequireStaffAndSuperuser2FAMiddleware(BaseRequire2FAMiddleware):
    def require_2fa(self, request):
        # Staff users and superusers are required to have 2FA.
        return request.user.is_staff or request.user.is_superuser


class TwoFactorMiddleware(MiddlewareMixin):
    """Reset the login flow if another page is loaded halfway through the login.

    (I.e. if the user has logged in with a username/password, but not yet entered their two-factor credentials.) This
    makes sure a user does not stay half logged in by mistake.

    """

    def process_request(self, request):
        try:
            match = get_resolver(request.urlconf).resolve(request.path)
            if (
                match
                and not match.url_name
                or not match.url_name.startswith("two-factor-authenticate")
            ):
                try:
                    del request.session["allauth_2fa_user_id"]
                except KeyError:
                    pass
        except Resolver404:
            pass
