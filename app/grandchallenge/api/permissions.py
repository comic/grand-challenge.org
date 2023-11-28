from django.conf import settings
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthenticated(BasePermission):
    """Allows access only to authenticated users.

    The original DRF permission is incompatible with the django guardian model.

    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.username.casefold()
            != settings.ANONYMOUS_USER_NAME.casefold()
        )


class IsAuthenticatedOrReadOnly(BasePermission):
    """The request is authenticated as a user, or is a read-only request.

    The original DRF permission is incompatible with the django guardian model.

    """

    def has_permission(self, request, view):
        return bool(
            request.method in SAFE_METHODS
            or request.user
            and request.user.username.casefold()
            != settings.ANONYMOUS_USER_NAME.casefold()
        )
