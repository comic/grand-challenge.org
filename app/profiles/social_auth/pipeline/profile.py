from guardian.shortcuts import assign_perm
from userena.managers import ASSIGNED_PERMISSIONS
from userena.models import UserenaSignup
from userena.utils import get_user_profile

from comicsite.models import set_project_admin_permissions


def create_profile(user=None, is_new=False, *args, **kwargs):
    """ Create user profile if necessary
    """
    if is_new:
        UserenaSignup.objects.get_or_create(user=user)

        # Give permissions to view and change profile
        for perm in ASSIGNED_PERMISSIONS['profile']:
            assign_perm(perm[0], user, get_user_profile(user=user))

        # Give permissions to view and change itself
        for perm in ASSIGNED_PERMISSIONS['user']:
            assign_perm(perm[0], user, user)

    return {'profile': get_user_profile(user=user)}


def set_project_permissions(user=None, profile=None, *args, **kwargs):
    """ Give the user the permission to do something with projects.
    """
    if not user or not user.is_authenticated():
        print("no user, or is not authenticated")
        return
    if profile:
        set_project_admin_permissions(None, user=user)
