from django.http import Http404
from rest_framework import exceptions, permissions


class ArchiveItemPermission(permissions.BasePermission):
    """
    Checks whether current user has permission to view or update the archive
    corresponding to the current archive item.
    """

    perms_map = {
        "GET": ["archives.view_archive"],
        "PUT": ["archives.upload_archive"],
        "PATCH": ["archives.upload_archive"],
    }

    def has_object_permission(self, request, view, obj):
        perm_obj = obj.archive
        perms = self._get_required_object_permissions(request.method)
        if not request.user.has_perms(perms, perm_obj):
            raise Http404
        return True

    def _get_required_object_permissions(self, method):
        if method not in self.perms_map:
            raise exceptions.MethodNotAllowed(method)
        return [perm for perm in self.perms_map[method]]
