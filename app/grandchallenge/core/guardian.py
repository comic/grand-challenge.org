from functools import cached_property

from django.contrib.auth.models import Permission
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Index
from guardian.core import ObjectPermissionChecker
from guardian.mixins import PermissionRequiredMixin  # noqa: I251
from guardian.models import GroupObjectPermission
from guardian.models import (  # noqa: I251
    GroupObjectPermissionBase as GroupObjectPermissionBaseOrig,
)
from guardian.models import UserObjectPermission
from guardian.models import (  # noqa: I251
    UserObjectPermissionBase as UserObjectPermissionBaseOrig,
)
from guardian.utils import (
    get_anonymous_user,
    get_group_obj_perms_model,
    get_user_obj_perms_model,
)
from rest_framework.filters import BaseFilterBackend


class ViewObjectPermissionListMixin:
    """
    Optimised version of guardian.mixins.PermissionListMixin

    A queryset filter that limits results to those where the requesting user
    has read object level permissions.
    """

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)

        return filter_by_permission(
            queryset=queryset,
            user=self.request.user,
            codename=f"view_{queryset.model._meta.model_name}",
        )


class ViewObjectPermissionsFilter(BaseFilterBackend):
    """
    Optimised version of rest_framework_guardian.filters.ObjectPermissionsFilter

    A filter backend that limits results to those where the requesting user
    has read object level permissions.
    """

    def filter_queryset(self, request, queryset, view):
        return filter_by_permission(
            queryset=queryset,
            user=request.user,
            codename=f"view_{queryset.model._meta.model_name}",
        )


class ObjectPermissionCheckerMixin:
    @cached_property
    def permission_checker(self):
        return ObjectPermissionChecker(user_or_group=self.request.user)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["checker"] = self.permission_checker
        return context


class ObjectPermissionRequiredMixin(PermissionRequiredMixin):
    accept_global_perms = False


class UserObjectPermissionBase(UserObjectPermissionBaseOrig):
    """
    Base user object permissions

    The allowed permissions should be a minimal set of codenames
    that are allowed to be assigned to the users for the related
    model in order to keep the permission filters fast.

    content_object must be a foreign key to the related model with
    on_delete=CASCADE.
    """

    allowed_permissions = None

    def save(self, *args, **kwargs):
        if not isinstance(self.allowed_permissions, frozenset):
            raise ImproperlyConfigured(
                f"{self.__class__}.allowed_permissions should be a frozenset"
            )

        if self.permission.codename not in self.allowed_permissions:
            raise RuntimeError(
                f"{self.permission.codename} should not be assigned to users for this model, "
                f"if it is required then please add it to {self.__class__}.allowed_permissions"
            )

        super().save(*args, **kwargs)

    class Meta(UserObjectPermissionBaseOrig.Meta):
        abstract = True
        indexes = [
            Index(fields=["user", "permission"]),
        ]


class GroupObjectPermissionBase(GroupObjectPermissionBaseOrig):
    """
    Base group object permissions

    The allowed permissions should be a minimal set of codenames
    that are allowed to be assigned to the groups for the related
    model in order to keep the permission filters fast.

    content_object must be a foreign key to the related model with
    on_delete=CASCADE.
    """

    allowed_permissions = None

    def save(self, *args, **kwargs):
        if not isinstance(self.allowed_permissions, frozenset):
            raise ImproperlyConfigured(
                f"{self.__class__}.allowed_permissions should be a frozenset"
            )

        if self.permission.codename not in self.allowed_permissions:
            raise RuntimeError(
                f"{self.permission.codename} should not be assigned to groups for this model, "
                f"if it is required then please add it to {self.__class__}.allowed_permissions"
            )

        super().save(*args, **kwargs)

    class Meta(GroupObjectPermissionBaseOrig.Meta):
        abstract = True
        indexes = [
            Index(fields=["group", "permission"]),
        ]


def filter_by_permission(*, queryset, user, codename):
    """
    Optimised version of get_objects_for_user

    This method considers both the group and user permissions, and ignores
    global permissions.

    Django guardian keeps its permissions in two tables. If you are allowing
    permissions from both users and groups then get_objects_for_user
    creates uses a SQL OR operation which is slow. This optimises the queries
    by using a SQL Union.

    This requires using direct foreign key permissions on the objects so that
    a reverse lookup can be used.
    """
    if user.is_superuser is True:
        return queryset

    if user.is_anonymous:
        # AnonymousUser does not work with filters
        user = get_anonymous_user()

    permission = Permission.objects.get(
        content_type__app_label=queryset.model._meta.app_label,
        codename=codename,
    )

    dfk_group_model = get_group_obj_perms_model(queryset.model)

    if isinstance(dfk_group_model, GroupObjectPermission):
        raise RuntimeError("DFK group permissions not active for model")

    dfk_user_model = get_user_obj_perms_model(queryset.model)

    if isinstance(dfk_user_model, UserObjectPermission):
        raise RuntimeError("DFK user permissions not active for model")

    group_filter_required = (
        permission.codename in dfk_group_model.allowed_permissions
    )
    user_filter_required = (
        permission.codename in dfk_user_model.allowed_permissions
    )

    group_related_query_name = (
        dfk_group_model.content_object.field.related_query_name()
    )

    # Evaluate the pks in python to force the use of the index
    group_pks = {*user.groups.values_list("pk", flat=True)}

    group_filter_kwargs = {
        f"{group_related_query_name}__group__pk__in": group_pks,
        f"{group_related_query_name}__permission": permission,
    }

    user_related_query_name = (
        dfk_user_model.content_object.field.related_query_name()
    )

    user_filter_kwargs = {
        f"{user_related_query_name}__user": user,
        f"{user_related_query_name}__permission": permission,
    }

    if group_filter_required and user_filter_required:
        pks = (
            queryset.filter(**user_filter_kwargs)
            .union(queryset.filter(**group_filter_kwargs))
            .values_list("pk", flat=True)
        )
        return queryset.filter(pk__in=pks)
    elif group_filter_required:
        return queryset.filter(**group_filter_kwargs)
    elif user_filter_required:
        return queryset.filter(**user_filter_kwargs)
    else:
        raise ImproperlyConfigured(
            f"No filter required for filtering this queryset by {permission.codename}. "
            "Please ensure this is set in allowed_permissions on "
            f"{dfk_group_model.__class__} or {dfk_user_model.__class__}."
        )


def get_object_if_allowed(*, model, pk, user, codename):
    try:
        obj = model.objects.get(pk=pk)
    except model.DoesNotExist:
        return

    if user.has_perm(codename, obj):
        return obj
