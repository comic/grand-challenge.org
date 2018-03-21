from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from challenges.models import ComicSiteModel, Challenge


def can_access(user, path, challenge_short_name):
    """ Does this user have permission to access folder path which is part of
    challenge named challenge_short_name?
    Override permission can be used to make certain folders servable through
    code even though this would not be allowed otherwise

    """
    required = _required_permission(path, challenge_short_name)
    if required == ComicSiteModel.ALL:
        return True

    elif required == ComicSiteModel.REGISTERED_ONLY:
        project = Challenge.objects.get(short_name=challenge_short_name)
        if project.is_participant(user):
            return True

        else:
            return False

    elif required == ComicSiteModel.ADMIN_ONLY:
        project = Challenge.objects.get(short_name=challenge_short_name)
        if project.is_admin(user):
            return True

        else:
            return False

    else:
        return False


def _required_permission(path, challenge_short_name):
    """ Given a file path on local filesystem, which permission level is needed
    to view this?

    """
    # some config checking.
    # TODO : check this once at server start but not every time this method is
    # called. It is too late to throw this error once a user clicks
    # something.
    if not hasattr(settings, "COMIC_PUBLIC_FOLDER_NAME"):
        raise ImproperlyConfigured(
            "Don't know from which folder serving publiv files"
            "is allowed. Please add a setting like "
            "'COMIC_PUBLIC_FOLDER_NAME = \"public_html\""
            " to your .conf file."
        )

    if not hasattr(settings, "COMIC_REGISTERED_ONLY_FOLDER_NAME"):
        raise ImproperlyConfigured(
            "Don't know from which folder serving protected files"
            "is allowed. Please add a setting like "
            "'COMIC_REGISTERED_ONLY_FOLDER_NAME = \"datasets\""
            " to your .conf file."
        )

    if challenge_short_name.lower() == 'mugshots':
        # Anyone can see mugshots
        return ComicSiteModel.ALL

    if challenge_short_name.lower() == 'evaluation':
        # No one can download evaluation files
        return 'nobody'

    if challenge_short_name.lower() == 'evaluation-supplementary':
        # Anyone can download supplementary files
        return ComicSiteModel.ALL

    if challenge_short_name.lower() == settings.JQFILEUPLOAD_UPLOAD_SUBIDRECTORY:
        # No one can download evaluation files
        return 'nobody'

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
