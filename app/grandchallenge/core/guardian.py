from functools import partial

from guardian.mixins import (  # noqa: I251
    PermissionListMixin as PermissionListMixinOrig,
)
from guardian.mixins import PermissionRequiredMixin  # noqa: I251
from guardian.shortcuts import (  # noqa: I251
    get_objects_for_group as get_objects_for_group_orig,
)
from guardian.shortcuts import (  # noqa: I251
    get_objects_for_user as get_objects_for_user_orig,
)

get_objects_for_user = partial(
    get_objects_for_user_orig, accept_global_perms=False
)

get_objects_for_group = partial(
    get_objects_for_group_orig, accept_global_perms=False
)


class PermissionListMixin(PermissionListMixinOrig):
    get_objects_for_user_extra_kwargs = {"accept_global_perms": False}


class ObjectPermissionRequiredMixin(PermissionRequiredMixin):
    accept_global_perms = False
