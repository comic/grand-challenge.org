from rest_framework import permissions


class ImagePermission(permissions.BasePermission):
    """
    Permission class for APIViews in retina app.
    Checks if user is in retina graders or admins group
    """

    def has_object_permission(self, request, view, obj):
        return request.user.has_perm("view_image", obj)
