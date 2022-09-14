from functools import partial

from guardian.shortcuts import (
    get_objects_for_user as get_objects_for_user_orig,
)

get_objects_for_user = partial(
    get_objects_for_user_orig, accept_global_perms=False
)
