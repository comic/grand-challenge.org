from django.conf import settings

from grandchallenge.challenges.models import ComicSiteModel, Challenge


def can_access(user, path, *, challenge: Challenge):
    """ Does this user have permission to access folder path which is part of
    challenge named challenge_short_name?
    Override permission can be used to make certain folders servable through
    code even though this would not be allowed otherwise

    """
    required = _required_permission(path)

    if required == ComicSiteModel.ALL:
        return True

    elif required == ComicSiteModel.REGISTERED_ONLY:
        return challenge.is_participant(user)

    elif required == ComicSiteModel.ADMIN_ONLY:
        return challenge.is_admin(user)

    elif required == ComicSiteModel.STAFF_ONLY:
        return user.is_staff

    else:
        return False


def _required_permission(path):
    """ Given a file path on local filesystem, which permission level is needed
    to view this?

    """
    if hasattr(settings, "COMIC_ADDITIONAL_PUBLIC_FOLDER_NAMES"):
        if startwith_any(path, settings.COMIC_ADDITIONAL_PUBLIC_FOLDER_NAMES):
            return ComicSiteModel.ALL

    if path.startswith(settings.COMIC_PUBLIC_FOLDER_NAME):
        return ComicSiteModel.ALL

    elif path.startswith(settings.COMIC_REGISTERED_ONLY_FOLDER_NAME):
        return ComicSiteModel.REGISTERED_ONLY

    else:
        return ComicSiteModel.ADMIN_ONLY


def startwith_any(path, start_options):
    """ Return true if path starts with any of the strings in string array
    start_options

    """
    for option in start_options:
        if path.startswith(option):
            return True

    return False
