from functools import partial

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
