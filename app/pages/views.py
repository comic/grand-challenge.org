import mimetypes
from os import path

from django.core.files import File
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from comicmodels.models import Page, ComicSiteModel
from comicsite.views import site_get_standard_vars, getRenderedPageIfAllowed, \
    get_data_folder_path
from filetransfers.api import serve_file


def page(request, site_short_name, page_title):
    """ show a single page on a site """

    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)
    currentpage = getRenderedPageIfAllowed(page_title, request, site)
    response = render(request, 'page.html', {'currentpage': currentpage})

    # TODO: THis has code smell. If page has to be checked like this, is it
    # ok to use a page object for error messages?
    if hasattr(currentpage, "is_error_page"):
        if currentpage.is_error_page:
            response.status_code = 403

    return response


def insertedpage(request, site_short_name, page_title, dropboxpath):
    """ show contents of a file from the local dropbox folder for this project

    """

    (mimetype, encoding) = mimetypes.guess_type(dropboxpath)

    if mimetype is None:
        mimetype = "NoneType"  # make the next statement not crash on non-existant mimetype

    if mimetype.startswith("image"):
        return inserted_file(request, site_short_name, dropboxpath)

    if mimetype == "application/pdf" or mimetype == "application/zip":
        return inserted_file(request, site_short_name, dropboxpath)

    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)

    p = get_object_or_404(Page, comicsite__short_name=site.short_name,
                          title=page_title)

    baselink = reverse('challenge-page',
                       kwargs={'site_short_name': p.comicsite.short_name,
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


def inserted_file(request, site_short_name, filepath=""):
    """ Get image from local dropbox and serve.

    """

    from filetransfers.views import can_access

    data_folder_root = get_data_folder_path(site_short_name)

    filename = path.join(data_folder_root, filepath)

    # can this location be served regularly (e.g. it is in public folder)?
    serve_allowed = can_access(request.user, filepath, site_short_name)

    # if not, linking to anywhere should be possible because it is convenient
    # and the security risk is not too great. TODO (is it not?)
    if not serve_allowed:
        serve_allowed = can_access(request.user,
                                   filepath,
                                   site_short_name,
                                   override_permission=ComicSiteModel.REGISTERED_ONLY)

    if serve_allowed:
        try:
            file = open(filename, "rb")
        except Exception:
            raise Http404

        django_file = File(file)
        return serve_file(request, django_file)

    else:
        return HttpResponseForbidden("This file is not available without "
                                     "credentials")
