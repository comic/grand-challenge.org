from userena.models import UserenaSignup
from profiles.models import UserProfile as Profile
from userena.managers import ASSIGNED_PERMISSIONS
from guardian.shortcuts import assign_perm
from userena.signals import signup_complete
from comicsite.models import get_or_create_projectadmingroup


def create_profile(user=None, profile=None, *args, **kwargs):
    """ Create user profile if necessary
    """
    if profile:
        return { 'profile':profile }
    if not user:
        return
    return { 'profile': Profile.objects.get_or_create(user=user)[0] }


def set_guardian_permissions(user=None, profile=None, *args, **kwargs):
    """ Give the user permission to modify themselves
    """
    if not user or not user.is_authenticated():
        return
    if profile:
        # Give permissions to view and change profile
        for perm in ASSIGNED_PERMISSIONS['profile']:
            assign_perm(perm[0], user, profile)
    # Give permissions to view and change itself
    for perm in ASSIGNED_PERMISSIONS['user']:
        assign_perm(perm[0], user, user)


def set_project_permissions(user=None, profile=None, *args, **kwargs):
    """ Give the user the permission to do something with projects.
    """
    if not user or not user.is_authenticated():
        print("no user, or is not authenticated")
        return
    if profile:
        projectadmingroup = get_or_create_projectadmingroup()
        user.groups.add(projectadmingroup)

        # set staff status so user can access admin interface. User will still have to
        # activate through email link before being able to log in at all.
        user.is_staff = True
        user.save()
