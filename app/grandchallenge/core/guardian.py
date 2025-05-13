from functools import cached_property, partial

from django.contrib.auth.models import Permission
from guardian.core import ObjectPermissionChecker
from guardian.mixins import (  # noqa: I251
    PermissionListMixin as PermissionListMixinOrig,
)
from guardian.mixins import PermissionRequiredMixin  # noqa: I251
from guardian.models import (
    GroupObjectPermission,
    GroupObjectPermissionBase,
    UserObjectPermission,
    UserObjectPermissionBase,
)
from guardian.shortcuts import (  # noqa: I251
    get_objects_for_group as get_objects_for_group_orig,
)
from guardian.shortcuts import (  # noqa: I251
    get_objects_for_user as get_objects_for_user_orig,
)
from guardian.utils import (
    get_anonymous_user,
    get_group_obj_perms_model,
    get_user_obj_perms_model,
)

get_objects_for_user = partial(
    get_objects_for_user_orig, accept_global_perms=False
)

get_objects_for_group = partial(
    get_objects_for_group_orig, accept_global_perms=False
)


class PermissionListMixin(PermissionListMixinOrig):
    get_objects_for_user_extra_kwargs = {"accept_global_perms": False}


class ObjectPermissionCheckerMixin:
    request = None

    @cached_property
    def permission_checker(self):
        return ObjectPermissionChecker(user_or_group=self.request.user)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["checker"] = self.permission_checker
        return context


class ObjectPermissionRequiredMixin(PermissionRequiredMixin):
    accept_global_perms = False


class NoUserPermissionsAllowed(UserObjectPermissionBase):
    def save(self, *args, **kwargs):
        raise RuntimeError(
            "User permissions should not be assigned for this model"
        )

    class Meta(UserObjectPermissionBase.Meta):
        abstract = True


class NoGroupPermissionsAllowed(GroupObjectPermissionBase):
    def save(self, *args, **kwargs):
        raise RuntimeError(
            "Group permissions should not be assigned for this model"
        )

    class Meta(GroupObjectPermissionBase.Meta):
        abstract = True


def filter_by_permission(*, queryset, user, codename, accept_user_perms=True):
    """
    Optimised version of get_objects_for_user

    This method considers both the group and user permissions, and ignores
    global permissions.

    Django guardian keeps its permissions in two tables. If you are allowing
    permissions from both users and groups then get_objects_for_user
    creates uses a SQL OR operation which is slow. This optimises the queries
    by using a SQL Union.

    This requires using direct foreign key permissions on the objects so that
    a reverse lookup can be used. Django does now allow filtering of
    querysets created with a SQL Union, so this must be the last operation
    in the queryset generation.
    """
    if user.is_superuser is True:
        return queryset

    if user.is_anonymous:
        # AnonymousUser does not work with filters
        user = get_anonymous_user()

    dfk_group_model = get_group_obj_perms_model(queryset.model)

    if isinstance(dfk_group_model, GroupObjectPermission):
        raise RuntimeError("DFK group permissions not active for model")

    group_related_query_name = (
        dfk_group_model.content_object.field.related_query_name()
    )

    permission = Permission.objects.get(
        content_type__app_label=queryset.model._meta.app_label,
        codename=codename,
    )

    group_pks = {*user.groups.values_list("pk", flat=True)}

    group_filter_kwargs = {
        f"{group_related_query_name}__group__pk__in": group_pks,
        f"{group_related_query_name}__permission": permission,
    }

    if accept_user_perms:
        dfk_user_model = get_user_obj_perms_model(queryset.model)

        if isinstance(dfk_user_model, UserObjectPermission):
            raise RuntimeError("DFK user permissions not active for model")

        user_related_query_name = (
            dfk_user_model.content_object.field.related_query_name()
        )

        user_filter_kwargs = {
            f"{user_related_query_name}__user": user,
            f"{user_related_query_name}__permission": permission,
        }

        pks = (
            queryset.filter(**user_filter_kwargs)
            .union(queryset.filter(**group_filter_kwargs))
            .values_list("pk", flat=True)
        )

        return queryset.filter(pk__in=pks)
    else:
        return queryset.filter(**group_filter_kwargs)


def get_object_if_allowed(*, model, pk, user, codename):
    try:
        obj = model.objects.get(pk=pk)
    except model.DoesNotExist:
        return

    if user.has_perm(codename, obj):
        return obj
