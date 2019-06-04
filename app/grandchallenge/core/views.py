from django.conf import settings
from django.core.files.storage import DefaultStorage
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.template import Template, TemplateSyntaxError, RequestContext
from django.utils._os import safe_join
from django.views.generic import TemplateView

from grandchallenge.pages.models import Page, ErrorPage


def challenge_homepage(request):
    challenge = request.challenge
    pages = challenge.page_set.all()

    if len(pages) == 0:
        currentpage = ErrorPage(
            challenge=challenge,
            title="no_pages_found",
            html="No pages found for this site. Please log in and add some pages.",
        )
    else:
        currentpage = pages[0]

    currentpage = getRenderedPageIfAllowed(currentpage, request)

    return render(
        request,
        "page.html",
        {"challenge": challenge, "currentpage": currentpage, "pages": pages},
    )


def renderTags(request, p, recursecount=0):
    """ render page contents using django template system
    This makes it possible to use tags like '{% dataset %}' in page content.
    If a rendered tag results in another tag, this can be rendered recursively
    as long as recurse limit is not exceeded.
    
    """
    recurselimit = 2
    try:
        t = Template("{% load grandchallenge_tags %}" + p.html)
    except TemplateSyntaxError as e:
        # when page contents cannot be rendered, just display raw contents and include error message on page
        errormsg = (
            '<span class="pageError"> Error rendering template: %s </span>' % e
        )
        pagecontents = p.html + errormsg
        return pagecontents

    # pass page to context here to be able to render tags based on which page does the rendering
    context = RequestContext(request, {"currentpage": p})
    pagecontents = t.render(context)

    if (
        "{%" in pagecontents or "{{" in pagecontents
    ):  # if rendered tags results in another tag, try to render this as well
        if recursecount < recurselimit:
            p2 = copy_page(p)
            p2.html = pagecontents
            return renderTags(request, p2, recursecount + 1)

        else:
            # when page contents cannot be rendered, just display raw contents and include error message on page
            errormsg = (
                '<span class="pageError"> Error rendering template: rendering recursed further than'
                + str(recurselimit)
                + " </span>"
            )
            pagecontents = p.html + errormsg
    return pagecontents


def permissionMessage(request, p):
    if request.user.is_authenticated:
        msg = """ <div class="system_message">
                <h2> Restricted page</h2>
                  
                  <p>This page can only be viewed by participants of this project to view this page please make sure of the following:</p>
                  
                  <ul>
                      <li>First, log in to this site by using the 'Sign in' button at the top right.</li>
                      <li>Second, you need to join / register with the specific project you are interested in as a participant. 
                      The link to do this is provided by the project organizers on the project website.</li>
                  </ul>
                  <div>
              """
        title = p.title
    else:
        msg = (
            "The page '"
            + p.title
            + "' can only be viewed by registered users. Please sign in to view this page."
        )
        title = p.title

    return ErrorPage(challenge=request.challenge, title=title, html=msg)


# TODO: could a decorator be better then all these ..IfAllowed pages?
def getRenderedPageIfAllowed(page_or_page_title, request):
    """ check permissions and render tags in page. If string title is given page is looked for 
        return nice message if not allowed to view"""
    if isinstance(page_or_page_title, bytes):
        page_or_page_title = page_or_page_title.decode()

    if isinstance(page_or_page_title, str):
        page_title = page_or_page_title
        try:
            p = request.challenge.page_set.get(title__iexact=page_title)
        except Page.DoesNotExist:
            raise Http404
    else:
        p = page_or_page_title

    if p.can_be_viewed_by(request.user):
        p.html = renderTags(request, p)
        currentpage = p
    else:
        currentpage = permissionMessage(request, p)

    return currentpage


def get_data_folder_path(challenge_short_name):
    """ Returns physical base path to the root of the folder where all files for
    this project are kept """
    return safe_join(settings.MEDIA_ROOT, challenge_short_name)


class HomeTemplate(TemplateView):
    template_name = "home.html"


def copy_page(page):
    return Page(challenge=page.challenge, title=page.title, html=page.html)
