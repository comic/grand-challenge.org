from allauth_2fa.middleware import BaseRequire2FAMiddleware


class RequireStaffAndSuperuser2FAMiddleware(BaseRequire2FAMiddleware):
    def require_2fa(self, request):
        # Staff users and superusers are required to have 2FA.
        return request.user.is_staff or request.user.is_superuser
