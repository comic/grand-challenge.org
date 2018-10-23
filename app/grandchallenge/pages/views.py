import mimetypes
import posixpath

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.files import File
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.utils._os import safe_join
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    RedirectView,
)
from favicon.models import Favicon

from grandchallenge.core.permissions.mixins import UserIsChallengeAdminMixin
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.core.views import (
    getRenderedPageIfAllowed,
    get_data_folder_path,
    getSite,
)
from grandchallenge.pages.forms import PageCreateForm, PageUpdateForm
from grandchallenge.pages.models import Page
from grandchallenge.serving.api import serve_file
from grandchallenge.serving.permissions import can_access


class ChallengeFilteredQuerysetMixin(object):
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(Q(challenge=self.request.challenge))


class ChallengeFormKwargsMixin(object):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"challenge": self.request.challenge})
        return kwargs


class PageCreate(
    UserIsChallengeAdminMixin, ChallengeFormKwargsMixin, CreateView
):
    model = Page
    form_class = PageCreateForm

    def form_valid(self, form):
        form.instance.challenge = self.request.challenge
        return super().form_valid(form)


class PageList(
    UserIsChallengeAdminMixin, ChallengeFilteredQuerysetMixin, ListView
):
    model = Page


class PageUpdate(
    UserIsChallengeAdminMixin,
    ChallengeFilteredQuerysetMixin,
    ChallengeFormKwargsMixin,
    UpdateView,
):
    model = Page
    form_class = PageUpdateForm
    slug_url_kwarg = "page_title"
    slug_field = "title__iexact"
    template_name_suffix = "_form_update"

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.move(form.cleaned_data["move"])
        return response


class PageDelete(
    UserIsChallengeAdminMixin, ChallengeFilteredQuerysetMixin, DeleteView
):
    model = Page
    slug_url_kwarg = "page_title"
    slug_field = "title__iexact"
    success_message = "Page was successfully deleted"

    def get_success_url(self):
        return reverse(
            "pages:list",
            kwargs={"challenge_short_name": self.request.challenge.short_name},
        )

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Legacy methods, moved from comicsite/views.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def page(request, challenge_short_name, page_title):
    """ show a single page on a site """

    site = getSite(challenge_short_name)

    currentpage = getRenderedPageIfAllowed(page_title, request, site)

    response = render(request, "page.html", {"currentpage": currentpage})

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
        mimetype = (
            "NoneType"
        )  # make the next statement not crash on non-existant mimetype
    if mimetype.startswith("image"):
        return inserted_file(request, challenge_short_name, dropboxpath)

    if mimetype == "application/pdf" or mimetype == "application/zip":
        return inserted_file(request, challenge_short_name, dropboxpath)

    site = getSite(challenge_short_name)

    p = get_object_or_404(
        Page, challenge__short_name=site.short_name, title=page_title
    )

    baselink = reverse(
        "pages:detail",
        kwargs={
            "challenge_short_name": p.challenge.short_name,
            "page_title": p.title,
        },
    )
    msg = (
        '<div class="breadcrumbtrail"> Displaying \''
        + dropboxpath
        + "' from local dropboxfolder, originally linked from\
           page <a href=\""
        + baselink
        + '">'
        + p.title
        + "</a> </div>"
    )
    p.html = "{% insert_file " + dropboxpath + " %} <br/><br/>" + msg

    currentpage = getRenderedPageIfAllowed(p, request, site)

    return render(
        request, "dropboxpage.html", {"site": site, "currentpage": currentpage}
    )


def inserted_file(request, challenge_short_name, filepath=""):
    """ Get image from local dropbox and serve.

    """
    data_folder_root = get_data_folder_path(challenge_short_name)
    filepath = posixpath.normpath(filepath).lstrip("/")
    filename = safe_join(data_folder_root, filepath)
    # can this location be served regularly (e.g. it is in public folder)?
    serve_allowed = can_access(
        request.user, filepath, challenge=request.challenge
    )
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
        return serve_file(django_file)

    else:
        return HttpResponseForbidden(
            "This file is not available without credentials."
        )


class FaviconView(RedirectView):
    """
    Some browsers do not follow the favicon links in base.html, so do this
    explicitly here.
    """

    permanent = False
    rel = "shortcut icon"

    def get_redirect_url(self, *args, **kwargs):
        fav = Favicon.objects.filter(isFavicon=True).first()

        if not fav:
            return None

        if self.rel == "shortcut icon":
            size = 32
        else:
            # This is the largest icon from
            # https://github.com/audreyr/favicon-cheat-sheet
            size = kwargs.get("size", 180)

        default_fav = fav.get_favicon(size=size, rel=self.rel)

        return default_fav.faviconImage.url
