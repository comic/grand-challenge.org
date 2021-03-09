from django.conf import settings
from django.contrib.auth.mixins import AccessMixin
from rest_framework import permissions


def is_in_retina_graders_group(user):
    """
    Checks if the user is in the retina graders group
    :param user: Django User model
    :return: true/false
    """
    return user.groups.filter(name=settings.RETINA_GRADERS_GROUP_NAME).exists()


def is_in_retina_admins_group(user):
    """
    Checks if the user is in the retina admins group
    :param user: Django User model
    :return: true/false
    """
    return user.groups.filter(name=settings.RETINA_ADMINS_GROUP_NAME).exists()


def is_in_retina_group(user):
    """
    Checks if the user is in the retina graders or retina admins group
    :param user: Django User model
    :return: true/false
    """
    return is_in_retina_graders_group(user) or is_in_retina_admins_group(user)


class RetinaAPIPermission(permissions.BasePermission):
    """
    Permission class for APIViews in retina app.
    Checks if user is in retina graders or admins group
    """

    def has_permission(self, request, view):
        return is_in_retina_group(request.user)


class RetinaAPIPermissionMixin(AccessMixin):
    """
    Mixin for non APIViews in retina app.
    Verify that the current user is in the retina_graders group.
    """

    def dispatch(self, request, *args, **kwargs):
        if not is_in_retina_group(request.user):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
