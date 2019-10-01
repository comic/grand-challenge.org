from rest_framework import permissions

from grandchallenge.serving.permissions import user_can_download_image


class ImagePermission(permissions.BasePermission):
    """
    Permission class for APIViews in retina app.
    Checks if user is in retina graders or admins group
    """

    def has_object_permission(self, request, view, obj):
        return user_can_download_image(user=request.user, image=obj)
