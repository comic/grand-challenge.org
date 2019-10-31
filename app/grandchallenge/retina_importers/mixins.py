from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import permissions


class RetinaImportPermission(permissions.BasePermission):
    """
    Permission class for importer views in retina app.
    Checks if user is RETINA_IMPORT_USER
    """

    def has_permission(self, request, view):
        import_user = get_user_model().objects.get(
            username=settings.RETINA_IMPORT_USER_NAME
        )
        return request.user == import_user
