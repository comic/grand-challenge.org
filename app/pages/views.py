import mimetypes
from os import path

from django.core.exceptions import PermissionDenied
from django.core.files import File
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView

from comicmodels.models import Page
from comicsite.core.urlresolvers import reverse
from comicsite.permissions.mixins import UserIsChallengeAdminMixin
from comicsite.views import (
    site_get_standard_vars,
    getRenderedPageIfAllowed,
    get_data_folder_path,
)
from filetransfers.api import serve_file
from filetransfers.views import can_access


class PageList(UserIsChallengeAdminMixin, ListView):
    model = Page

    def get_queryset(self):
        queryset = super(PageList, self).get_queryset()

        return queryset.filter(Q(comicsite__pk=self.request.project_pk))


def page(request, challenge_short_name, page_title):
    """ show a single page on a site """

    [site, pages, metafooterpages] = site_get_standard_vars(
        challenge_short_name)
    currentpage = getRenderedPageIfAllowed(page_title, request, site)
    response = render(request, 'page.html', {'currentpage': currentpage})

    # TODO: THis has code smell. If page has to be checked like this, is it
    # ok to use a page object for error messages?
    if hasattr(currentpage, "is_error_page"):
        if currentpage.is_error_page:
            response.status_code = 403

    return response


def insertedpage(request, challenge_short_name, page_title, dropboxpath):
    """ show contents of a file from the local dropbox folder for this project

    """

    (mimetype, encoding) = mimetypes.guess_type(dropboxpath)

    if mimetype is None:
        mimetype = "NoneType"  # make the next statement not crash on non-existant mimetype

    if mimetype.startswith("image"):
        return inserted_file(request, challenge_short_name, dropboxpath)

    if mimetype == "application/pdf" or mimetype == "application/zip":
        return inserted_file(request, challenge_short_name, dropboxpath)

    [site, pages, metafooterpages] = site_get_standard_vars(
        challenge_short_name)

    p = get_object_or_404(Page, comicsite__short_name=site.short_name,
                          title=page_title)

    baselink = reverse('pages:detail',
                       kwargs={'challenge_short_name': p.comicsite.short_name,
                               'page_title': p.title})

    msg = "<div class=\"breadcrumbtrail\"> Displaying '" + dropboxpath + "' from local dropboxfolder, originally linked from\
           page <a href=\"" + baselink + "\">" + p.title + "</a> </div>"
    p.html = "{% insert_file " + dropboxpath + " %} <br/><br/>" + msg

    currentpage = getRenderedPageIfAllowed(p, request, site)

    return render(
        request,
        'dropboxpage.html',
        {
            'site': site,
            'currentpage': currentpage,
            "pages": pages,
            "metafooterpages": metafooterpages
        },
    )


def inserted_file(request, challenge_short_name, filepath=""):
    """ Get image from local dropbox and serve.

    """
    data_folder_root = get_data_folder_path(challenge_short_name)

    filename = path.join(data_folder_root, filepath)

    # can this location be served regularly (e.g. it is in public folder)?
    serve_allowed = can_access(request.user, filepath, challenge_short_name)

    if not serve_allowed:
        raise PermissionDenied(
            "You do not have the correct permissions to access this page."
        )

    if serve_allowed:
        try:
            file = open(filename, "rb")
        except Exception:
            raise Http404

        django_file = File(file)
        return serve_file(request, django_file)

    else:
        return HttpResponseForbidden(
            "This file is not available without credentials."
        )
