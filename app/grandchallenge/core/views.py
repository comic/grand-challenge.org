from django.conf import settings
from django.core.files.storage import DefaultStorage
from django.http import Http404
from django.shortcuts import render
from django.template import Template, TemplateSyntaxError, RequestContext
from django.utils._os import safe_join

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.pages.models import Page, ErrorPage


def site(request, challenge_short_name):
    try:
        site = getSite(challenge_short_name)
    except Challenge.DoesNotExist:
        raise Http404("Project %s does not exist" % challenge_short_name)

    pages = site.page_set.all()

    if len(pages) == 0:
        currentpage = ErrorPage(
            challenge=site,
            title="no_pages_found",
            html="No pages found for this site. Please log in and add some pages.",
        )
    else:
        currentpage = pages[0]

    currentpage = getRenderedPageIfAllowed(currentpage, request, site)

    return render(
        request,
        "page.html",
        {"site": site, "currentpage": currentpage, "pages": pages},
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


def permissionMessage(request, site, p):
    if request.user.is_authenticated:
        msg = """ <div class="system_message">
                <h2> Restricted page</h2>
                  
                  <p>This page can only be viewed by participants of this project to view this page please make sure of the following:</p>
                  
                  <ul>
                      <li>First, log in to {} by using the 'Sign in' button at the top right.</li>
                      <li>Second, you need to join / register with the specific project you are interested in as a participant. 
                      The link to do this is provided by the project organizers on the project website.</li>
                  </ul>
                  <div>
              """.format(
            settings.MAIN_PROJECT_NAME
        )
        title = p.title
    else:
        msg = (
            "The page '"
            + p.title
            + "' can only be viewed by registered users. Please sign in to view this page."
        )
        title = p.title

    return ErrorPage(challenge=site, title=title, html=msg)


# TODO: could a decorator be better then all these ..IfAllowed pages?
def getRenderedPageIfAllowed(page_or_page_title, request, site):
    """ check permissions and render tags in page. If string title is given page is looked for 
        return nice message if not allowed to view"""
    if isinstance(page_or_page_title, bytes):
        page_or_page_title = page_or_page_title.decode()

    if isinstance(page_or_page_title, str):
        page_title = page_or_page_title
        try:
            p = site.page_set.get(title__iexact=page_title)
        except Page.DoesNotExist:
            raise Http404
    else:
        p = page_or_page_title

    if p.can_be_viewed_by(request.user):
        p.html = renderTags(request, p)
        currentpage = p
    else:
        currentpage = permissionMessage(request, site, p)

    return currentpage


def get_data_folder_path(challenge_short_name):
    """ Returns physical base path to the root of the folder where all files for
    this project are kept """
    return safe_join(settings.MEDIA_ROOT, challenge_short_name)


def get_dirnames(path):
    """ Get all directory names in path as list of strings
            
    Raises: OSError if directory can not be found
    """
    storage = DefaultStorage()
    dirnames = storage.listdir(path)[0]
    dirnames.sort()
    return dirnames


def comicmain(request, page_title=""):
    """ show content as main page item. Loads pages from the main project """
    challenge_short_name = settings.MAIN_PROJECT_NAME

    try:
        site = getSite(challenge_short_name)
    except Challenge.DoesNotExist:
        link = reverse("challenges:create")
        link = link + "?short_name=%s" % challenge_short_name
        link_html = create_HTML_a(
            link, "Create project '%s'" % challenge_short_name
        )
        html = """I'm trying to show the first page for main project '%s' here,
        but '%s' does not exist. %s.""" % (
            challenge_short_name,
            challenge_short_name,
            link_html,
        )
        page = create_temp_page(title="no_pages_found", html=html)

        return render(
            request,
            "temppage.html",
            {"site": page.challenge, "currentpage": page},
        )

    pages = site.page_set.all()

    if len(pages) == 0:
        link = reverse("pages:list", args=[challenge_short_name])
        link_html = create_HTML_a(link, "admin interface")
        html = """I'm trying to show the first page for main project '%s' here,
        but '%s' contains no pages. Please add
        some in the %s.""" % (
            challenge_short_name,
            challenge_short_name,
            link_html,
        )
        page = create_temp_page(title="no_pages_found", html=html)

        return render(
            request,
            "temppage.html",
            {"site": page.challenge, "currentpage": page},
        )

    if page_title:
        pages = [p for p in pages if p.title.lower() == page_title.lower()]

        if len(pages) != 1:
            raise ValueError(
                f"More than 1 page with title {page_title} was found for {site}"
            )

    page = pages[0]
    page.html = renderTags(request, page)

    return render(request, "page.html", {"currentpage": page})


# ======================================== not called directly from urls.py ==
def getSite(challenge_short_name):
    return Challenge.objects.get(short_name__iexact=challenge_short_name)


def create_HTML_a(link_url, link_text):
    return '<a href="' + link_url + '">' + link_text + "</a>"


def create_HTML_a_img(link_url, image_url):
    """ create a linked image """
    img = '<img src="' + image_url + '">'
    linked_image = create_HTML_a(link_url, img)
    return linked_image


def copy_page(page):
    return Page(challenge=page.challenge, title=page.title, html=page.html)


def create_temp_page(title="temp_page", html=""):
    """ Create a quick mockup page which you can show, without needing to read 
    anything from database
    
    """
    site = Challenge()  # any page requires a site, create on the fly here.
    site.short_name = "Temp"
    site.name = "Temporary page"
    site.skin = ""
    return Page(challenge=site, title=title, html=html)
