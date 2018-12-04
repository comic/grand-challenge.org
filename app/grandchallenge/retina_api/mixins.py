from django.contrib.auth.mixins import AccessMixin
from rest_framework import permissions
from django.conf import settings


# Permission class for APIViews
class RetinaAPIPermission(permissions.BasePermission):
    # Perform permission check
    def has_permission(self, request, view):
        # TODO specific permissions?
        # uncomment next line and fix all tests accordingly to only allow users from retina_graders group
        # return self.request.user.groups.filter(name=settings.RETINA_GRADERS_GROUP_NAME).exists()
        print(request.user.username)
        return bool(request.user and request.user.is_authenticated)


# Mixin for non APIViews
class RetinaAPIPermissionMixin(AccessMixin):
    """Verify that the current user is authenticated."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
    # TODO modify to correct permissions check
