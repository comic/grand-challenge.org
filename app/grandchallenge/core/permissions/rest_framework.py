from rest_framework.permissions import DjangoObjectPermissions


class DjangoObjectOnlyPermissions(DjangoObjectPermissions):
    """
    Workaround for using object permissions without setting model perms,
    which is required by the implementation in Django Rest Framework. It
    enforces that the user is logged in so that the permissions can be checked
    later.

    See similar issue detailed here:
    https://stackoverflow.com/questions/34371409/
    """

    def has_permission(self, request, view):
        # Workaround to ensure DjangoModelPermissions are not applied
        # to the root view when using DefaultRouter.
        if getattr(view, "_ignore_model_permissions", False):
            return True

        if not request.user or (
            not request.user.is_authenticated and self.authenticated_users_only
        ):
            return False

        return True


class DjangoObjectOnlyWithCustomPostPermissions(DjangoObjectOnlyPermissions):
    """Grant all authenticated users POST permissions."""

    perms_map = {
        "GET": [],
        "OPTIONS": [],
        "HEAD": [],
        "POST": [],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }
