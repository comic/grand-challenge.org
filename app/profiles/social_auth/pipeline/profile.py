from urllib.parse import urljoin

from django.conf import settings
from django.shortcuts import redirect
from guardian.shortcuts import assign_perm
from userena.managers import ASSIGNED_PERMISSIONS
from userena.models import UserenaSignup
from userena.utils import get_user_profile

from comicsite.models import get_or_create_projectadmingroup


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
        projectadmingroup = get_or_create_projectadmingroup()
        user.groups.add(projectadmingroup)

        # set staff status so user can access admin interface. User will still have to
        # activate through email link before being able to log in at all.
        user.is_staff = True
        user.save()


def redirect_subdomain(strategy, *args, **kwargs):
    """
    Special handling for redirects for social auth and SUBDOMAIN_IS_PROJECTNAME
    """
    if settings.SUBDOMAIN_IS_PROJECTNAME:
        subdomain = strategy.session_get('sd')
        location = strategy.session_get('loc')

        protocol, domainname = settings.MAIN_HOST_NAME.split("//")
        url = protocol + "//"

        if len(subdomain) > 0:
            url += subdomain + '.'

        url += domainname

        url = urljoin(url, location)

        return redirect(url)
