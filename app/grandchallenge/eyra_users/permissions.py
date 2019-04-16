from rest_framework import exceptions
from rest_framework.permissions import DjangoModelPermissions
from django.contrib.auth.models import User


class EyraDjangoModelPermissions(DjangoModelPermissions):
    """
    The same as DjangoModelPermission, but also checks
    permissions for guardian's AnonymousUser
    """
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

    def has_permission(self, request, view):
        if getattr(view, '_ignore_model_permissions', False):
            return True

        user = request.user
        if not user.is_authenticated:  # user is Django AnonymousUser
            user = User.get_anonymous()  # guardians AnonymousUser

        queryset = self._queryset(view)
        perms = self.get_required_permissions(request.method, queryset.model)

        return user.has_perms(perms)


class EyraDjangoModelOrObjectPermissions(EyraDjangoModelPermissions):
    def get_required_object_permissions(self, method, model_cls):
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name
        }

        if method not in self.perms_map:
            raise exceptions.MethodNotAllowed(method)

        return [perm % kwargs for perm in self.perms_map[method]]

    def has_object_permission(self, request, view, obj):
        if EyraDjangoModelPermissions.has_permission(self, request, view):
            return True
        queryset = self._queryset(view)
        model_cls = queryset.model
        user = request.user

        perms = self.get_required_object_permissions(request.method, model_cls)

        return user.has_perms(perms, obj)

    def has_permission(self, request, view):
        handler = getattr(view, request.method.lower(), None)

        if handler and handler.__name__ == 'list':
            return EyraDjangoModelPermissions.has_permission(self, request, view)

        return True


# EyraPermissions:
# A user has permission if he has permissions on the whole model, OR specific permissions
# for an object (a model instance).
# ideally, we could express it like this, but it doesn't work because of how DRF imlements checking of ObjectPermissions
# EyraPermissions = EyraDjangoModelPermissions | EyraDjangoObjectPermissions
# see https://github.com/encode/django-rest-framework/issues/6596
EyraPermissions = EyraDjangoModelOrObjectPermissions