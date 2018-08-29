# -*- coding: utf-8 -*-
import os
import posixpath
from urllib.parse import unquote

from django.conf import settings
from django.core.files import File
from django.core.files.storage import DefaultStorage
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.views.generic import RedirectView

from grandchallenge.challenges.models import Challenge
from grandchallenge.serving.api import serve_file
from grandchallenge.serving.permissions import can_access


def sanitize_path(*, path: str):
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

    return newpath


def serve_challenge_file(request, challenge_short_name, path):
    """
    Serve static file for a given project.

    This is meant as a replacement for the inefficient debug only
    'django.views.static.serve' way of serving files under /media urls.

    """
    newpath = sanitize_path(path=path)

    if path != newpath:
        return HttpResponseRedirect(newpath)

    challenge = get_object_or_404(
        Challenge, short_name__iexact=challenge_short_name
    )

    fullpath = os.path.join(settings.MEDIA_ROOT, challenge.short_name, newpath)

    storage = DefaultStorage()

    if storage.exists(fullpath) and can_access(
        request.user, newpath, challenge.short_name
    ):
        try:
            f = storage.open(fullpath, "rb")
            file = File(f)
            return serve_file(file, save_as=True)
        except IOError:
            pass

    raise Http404("File not found.")


class ChallengeServeRedirect(RedirectView):
    # Do not redirect to a view name as this could skip some other handlers

    def get_redirect_url(self, *args, **kwargs):
        return f"/media/{kwargs['challenge_short_name']}/{kwargs['path']}/"
