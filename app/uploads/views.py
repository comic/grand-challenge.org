import os
import posixpath
from urllib.parse import unquote

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files import File
from django.core.files.storage import DefaultStorage
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.views.generic import ListView

from comicmodels.models import UploadModel, ComicSiteModel, ComicSite
from comicsite.permissions.mixins import UserIsChallengeAdminMixin
from uploads.api import serve_file
from pages.views import ComicSiteFilteredQuerysetMixin


class UploadList(UserIsChallengeAdminMixin, ComicSiteFilteredQuerysetMixin,
                 ListView):
    model = UploadModel


def can_access(user, path, project_name):
    """ Does this user have permission to access folder path which is part of
    project named project_name?
    Override permission can be used to make certain folders servable through
    code even though this would not be allowed otherwise

    """
    required = _required_permission(path, project_name)

    if required == ComicSiteModel.ALL:
        return True
    elif required == ComicSiteModel.REGISTERED_ONLY:
        project = ComicSite.objects.get(short_name=project_name)
        if project.is_participant(user):
            return True
        else:
            return False
    elif required == ComicSiteModel.ADMIN_ONLY:
        project = ComicSite.objects.get(short_name=project_name)
        if project.is_admin(user):
            return True
        else:
            return False
    else:
        return False


def _required_permission(path, project_name):
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
            " to your .conf file.")

    if not hasattr(settings, "COMIC_REGISTERED_ONLY_FOLDER_NAME"):
        raise ImproperlyConfigured(
            "Don't know from which folder serving protected files"
            "is allowed. Please add a setting like "
            "'COMIC_REGISTERED_ONLY_FOLDER_NAME = \"datasets\""
            " to your .conf file.")

    if project_name.lower() == 'mugshots':
        # Anyone can see mugshots
        return ComicSiteModel.ALL

    if project_name.lower() == 'evaluation':
        # No one can download evaluation files
        return 'nobody'

    if project_name.lower() == 'evaluation-supplementary':
        # Anyone can download supplementary files
        return ComicSiteModel.ALL

    if project_name.lower() == settings.JQFILEUPLOAD_UPLOAD_SUBIDRECTORY:
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
    """ Return true if path starts with any of the strings in string array start_options

    """
    for option in start_options:
        if path.startswith(option):
            return True

    return False


def serve(request, project_name, path, document_root=None):
    """
    Serve static file for a given project.

    This is meant as a replacement for the inefficient debug only
    'django.views.static.serve' way of serving files under /media urls.

    """

    if document_root is None:
        document_root = settings.MEDIA_ROOT

    path = posixpath.normpath(unquote(path))
    path = path.lstrip('/')
    newpath = ''
    for part in path.split('/'):
        if not part:
            # Strip empty path components.
            continue
        drive, part = os.path.splitdrive(part)
        head, part = os.path.split(part)
        if part in (os.curdir, os.pardir):
            # Strip '.' and '..' in path.
            continue
        newpath = os.path.join(newpath, part).replace('\\', '/')
    if newpath and path != newpath:
        return HttpResponseRedirect(newpath)
    fullpath = os.path.join(document_root, project_name, newpath)

    storage = DefaultStorage()

    if not storage.exists(fullpath):

        # On case sensitive filesystems you can have problems if the project
        # nameurl in the url is not exactly the same case as the filepath.
        # find the correct case for projectname then.

        projectlist = ComicSite.objects.filter(short_name=project_name)
        if not projectlist:
            raise Http404("project '%s' does not exist" % project_name)

        project_name = projectlist[0].short_name
        fullpath = os.path.join(document_root, project_name, newpath)

    if not storage.exists(fullpath):
        raise Http404('"%(path)s" does not exist' % {'path': fullpath})

    if can_access(request.user, path, project_name):
        try:
            f = storage.open(fullpath, 'rb')
            file = File(f)  # create django file object
        except IOError:
            return HttpResponseForbidden("This is not a file")

        # Do not offer to save images, but show them directly
        return serve_file(file, save_as=True)
    else:
        return HttpResponseForbidden("This file is not available without "
                                     "credentials")
