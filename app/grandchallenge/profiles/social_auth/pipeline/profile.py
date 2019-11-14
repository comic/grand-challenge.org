from guardian.shortcuts import assign_perm
from userena.managers import ASSIGNED_PERMISSIONS
from userena.models import UserenaSignup
from userena.utils import get_user_profile


def create_profile(user=None, is_new=False, *args, **kwargs):
    """Create user profile if necessary."""
    if is_new:
        UserenaSignup.objects.get_or_create(user=user)
        # Give permissions to view and change profile
        for perm in ASSIGNED_PERMISSIONS["profile"]:
            assign_perm(perm[0], user, get_user_profile(user=user))
        # Give permissions to view and change itself
        for perm in ASSIGNED_PERMISSIONS["user"]:
            assign_perm(perm[0], user, user)
    return {"profile": get_user_profile(user=user)}
