# -*- coding: utf-8 -*-
import os
import posixpath
from urllib.parse import unquote

from django.conf import settings
from django.core.files import File
from django.core.files.storage import DefaultStorage
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.views.generic import RedirectView

from grandchallenge.challenges.models import Challenge
from grandchallenge.serving.permissions import can_access
from grandchallenge.serving.api import serve_file


def serve(request, challenge_short_name, path, document_root=None):
    """
    Serve static file for a given project.

    This is meant as a replacement for the inefficient debug only
    'django.views.static.serve' way of serving files under /media urls.

    """
    if document_root is None:
        document_root = settings.MEDIA_ROOT
    path = posixpath.normpath(unquote(path))
    path = path.lstrip("/")
    newpath = ""
    for part in path.split("/"):
        if not part:
            # Strip empty path components.
            continue

        drive, part = os.path.splitdrive(part)
        head, part = os.path.split(part)
        if part in (os.curdir, os.pardir):
            # Strip '.' and '..' in path.
            continue

        newpath = os.path.join(newpath, part).replace("\\", "/")
    if newpath and path != newpath:
        return HttpResponseRedirect(newpath)

    fullpath = os.path.join(document_root, challenge_short_name, newpath)
    storage = DefaultStorage()
    if not storage.exists(fullpath):
        # On case sensitive filesystems you can have problems if the project
        # nameurl in the url is not exactly the same case as the filepath.
        # find the correct case for projectname then.
        projectlist = Challenge.objects.filter(
            short_name__iexact=challenge_short_name
        )
        if not projectlist:
            raise Http404("project '%s' does not exist" % challenge_short_name)

        challenge_short_name = projectlist[0].short_name
        fullpath = os.path.join(document_root, challenge_short_name, newpath)
    if not storage.exists(fullpath):
        raise Http404('"%(path)s" does not exist' % {"path": fullpath})

    if can_access(request.user, path, challenge_short_name):
        try:
            f = storage.open(fullpath, "rb")
            file = File(f)  # create django file object
        except IOError:
            return HttpResponseForbidden("This is not a file")

        # Do not offer to save images, but show them directly
        return serve_file(file, save_as=True)

    else:
        return HttpResponseForbidden(
            "This file is not available without " "credentials"
        )


class ChallengeServeRedirect(RedirectView):
    # Do not redirect to a view name as this could skip some other handlers

    def get_redirect_url(self, *args, **kwargs):
        return f"/media/{kwargs['challenge_short_name']}/{kwargs['path']}"
