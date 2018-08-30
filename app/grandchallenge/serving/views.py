# -*- coding: utf-8 -*-
import os
import posixpath

from django.conf import settings
from django.core.files import File
from django.core.files.storage import DefaultStorage
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils._os import safe_join
from django.views.generic import RedirectView

from grandchallenge.cases.models import Image
from grandchallenge.challenges.models import Challenge
from grandchallenge.serving.api import serve_file
from grandchallenge.serving.permissions import (
    can_access,
    user_can_download_imageset,
)


def serve_fullpath(*, fullpath):
    storage = DefaultStorage()

    if not (os.path.abspath(fullpath) == fullpath) or not storage.exists(
        fullpath
    ):
        raise Http404("File not found.")

    try:
        f = storage.open(fullpath, "rb")
        file = File(f)
        return serve_file(file, save_as=True)
    except IOError:
        raise Http404("File not found.")


def serve_folder(request, *, challenge_short_name=None, folder=None, path):
    """
    Serve static files in a folder.

    If the file is in a challenge folder, then the subfolders of this challenge
    will be checked for permissions, see `can_access`.

    If the challenge_short_name is not set, then the folder must be set.
    ALL FILES IN THIS FOLDER WILL BE AVAILABLE TO DOWNLOAD.
    """
    path = posixpath.normpath(path).lstrip("/")

    if challenge_short_name:
        if folder:
            raise AttributeError(
                "Only challenge_short_name or folder should be set"
            )

        challenge = get_object_or_404(
            Challenge, short_name__iexact=challenge_short_name
        )

        document_root = safe_join(settings.MEDIA_ROOT, challenge.short_name)
        fullpath = safe_join(document_root, path)
        allowed = can_access(
            request.user,
            fullpath[len(document_root) :].lstrip("/"),
            challenge=challenge,
        )
    elif folder:
        document_root = safe_join(settings.MEDIA_ROOT, folder)
        fullpath = safe_join(document_root, path)
        allowed = True
    else:
        raise AttributeError("challenge_short_name or folder must be set")

    if not allowed:
        raise Http404("File not found.")

    return serve_fullpath(fullpath=fullpath)


def serve_images(request, *, pk, path):
    try:
        # TODO: make sure that this imagefile belongs to this image
        image = Image.objects.get(pk=pk)

        imagesets = image.imagesets.all().select_related("challenge")

        for imageset in imagesets:
            if user_can_download_imageset(
                user=request.user, imageset=imageset
            ):
                # This image belongs to an imageset that
                # this user has access to
                break
        else:
            # No break in for loop, so user cannot download this
            raise Http404("File not found.")

    except Image.DoesNotExist:
        raise Http404("File not found.")

    document_root = safe_join(settings.MEDIA_ROOT, "images", pk)
    path = posixpath.normpath(path).lstrip("/")

    fullpath = safe_join(document_root, path)

    return serve_fullpath(fullpath=fullpath)


class ChallengeServeRedirect(RedirectView):
    # Do not redirect to a view name as this could skip some other handlers

    def get_redirect_url(self, *args, **kwargs):
        return f"/media/{kwargs['challenge_short_name']}/{kwargs['path']}/"
