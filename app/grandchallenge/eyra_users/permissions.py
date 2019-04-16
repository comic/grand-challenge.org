from django.http import Http404
from rest_framework import exceptions
from rest_framework.permissions import BasePermission
from django.contrib.auth.models import User


class EyraDjangoModelPermissions(BasePermission):
    """
    The same as DjangoModelPermission, but also checks
    permissions for guardian's AnonymousUser
    """

    # Map methods into required permission codes.
    # Override this if you need to also provide 'view' permissions,
    # or if you want to provide custom permission codes.
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

    def get_required_permissions(self, method, model_cls):
        """
        Given a model and an HTTP method, return the list of permission
        codes that the user is required to have.
        """
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name
        }

        if method not in self.perms_map:
            raise exceptions.MethodNotAllowed(method)

        return [perm % kwargs for perm in self.perms_map[method]]

    def _queryset(self, view):
        assert hasattr(view, 'get_queryset') \
            or getattr(view, 'queryset', None) is not None, (
            'Cannot apply {} on a view that does not set '
            '`.queryset` or have a `.get_queryset()` method.'
        ).format(self.__class__.__name__)

        if hasattr(view, 'get_queryset'):
            queryset = view.get_queryset()
            assert queryset is not None, (
                '{}.get_queryset() returned None'.format(view.__class__.__name__)
            )
            return queryset
        return view.queryset

    def has_permission(self, request, view):
        # Workaround to ensure DjangoModelPermissions are not applied
        # to the root view when using DefaultRouter.
        if getattr(view, '_ignore_model_permissions', False):
            return True

        # if not request.user or (
        #    not request.user.is_authenticated and self.authenticated_users_only):
        #     return False

        user = request.user
        if not user.is_authenticated:  # user is Django AnonymousUser
            user = User.get_anonymous()  # guardians AnonymousUser

        queryset = self._queryset(view)
        perms = self.get_required_permissions(request.method, queryset.model)

        return user.has_perms(perms)


SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')


class EyraDjangoObjectPermissions(EyraDjangoModelPermissions):
    def get_required_object_permissions(self, method, model_cls):
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name
        }

        if method not in self.perms_map:
            raise exceptions.MethodNotAllowed(method)

        return [perm % kwargs for perm in self.perms_map[method]]

    def has_object_permission(self, request, view, obj):
        # authentication checks have already executed via has_permission
        queryset = self._queryset(view)
        model_cls = queryset.model
        user = request.user

        perms = self.get_required_object_permissions(request.method, model_cls)

        return user.has_perms(perms, obj)

    def has_permission(self, request, view):
        return True

    
# EyraPermissions:
# A user has permission if he has permissions on the whole model, OR specific permissions
# for an object (a model instance).
EyraPermissions = EyraDjangoModelPermissions | EyraDjangoObjectPermissions
