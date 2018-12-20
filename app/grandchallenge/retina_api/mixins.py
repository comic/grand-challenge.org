from django.contrib.auth.mixins import AccessMixin
from rest_framework import permissions
from django.conf import settings


# Permission class for APIViews
class RetinaAPIPermission(permissions.BasePermission):
    # Perform permission check
    def has_permission(self, request, view):
        return request.user.groups.filter(name=settings.RETINA_GRADERS_GROUP_NAME).exists()


# Mixin for non APIViews
class RetinaAPIPermissionMixin(AccessMixin):
    """Verify that the current user is in the retina_graders group."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name=settings.RETINA_GRADERS_GROUP_NAME).exists():
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
