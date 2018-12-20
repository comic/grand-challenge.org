from django.contrib.auth.mixins import AccessMixin
from rest_framework import permissions
from django.conf import settings
from django.contrib.auth import get_user_model


def is_in_retina_graders_group(user):
    # Checks if the user is in the retina graders group
    return user.groups.filter(name=settings.RETINA_GRADERS_GROUP_NAME).exists()


def is_in_retina_admins_group(user):
    # Checks if the user is in the retina admins group
    return user.groups.filter(name=settings.RETINA_ADMINS_GROUP_NAME).exists()


def is_in_retina_group(user):
    # Checks if the user is in the retina graders or retina admins group
    return is_in_retina_graders_group(user) or is_in_retina_admins_group(user)


# Permission class for APIViews
class RetinaAPIPermission(permissions.BasePermission):
    # Perform permission check
    def has_permission(self, request, view):
        return is_in_retina_group(request.user)


# Permission class for annotation APIViews
class RetinaOwnerAPIPermission(permissions.BasePermission):
    # Checks if user is in retina admins group or is owner of this object
    def has_permission(self, request, view):
        username = view.kwargs.get("username")
        user = get_user_model().objects.get(username=username.lower())
        is_owner = request.user == user
        return is_in_retina_admins_group(request.user) or is_owner


# Mixin for non APIViews
class RetinaAPIPermissionMixin(AccessMixin):
    """Verify that the current user is in the retina_graders group."""
    def dispatch(self, request, *args, **kwargs):
        if not is_in_retina_group(request.user):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
