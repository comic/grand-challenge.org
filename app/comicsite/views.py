from os import path

from django.conf import settings
from django.core.files.storage import DefaultStorage
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import render
from django.template import Template, TemplateSyntaxError
from django.template.defaulttags import VerbatimNode

from comicmodels.models import (
    ComicSite,
    Page,
    ErrorPage,
)
from comicsite.core.urlresolvers import reverse
from comicsite.template.context import ComicSiteRequestContext


def site(request, site_short_name):
    # TODO: Doing two calls to getSite here. (second one in site_get_standard_vars)
    # How to handle not found nicely? Throwing exception in site_get_standard_vars
    # seems like a nice start, but this function is called throughout the code
    # also outside views (in contextprocessor). Throwing Http404 there will 
    # result in server error..

    try:
        site = getSite(site_short_name)
    except ComicSite.DoesNotExist:
        raise Http404("Project %s does not exist" % site_short_name)

    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)

    if len(pages) == 0:
        page = ErrorPage(comicsite=site, title="no_pages_found",
                         html="No pages found for this site. Please log in and use the admin button to add pages.")
        currentpage = page
    else:
        currentpage = pages[0]

    currentpage = getRenderedPageIfAllowed(currentpage, request, site)

    return render(
        request,
        'page.html',
        {
            'site': site,
            'currentpage': currentpage,
            "pages": pages,
        },
    )


def site_get_standard_vars(site_short_name):
    """ When rendering a site you need to pass the current site, all pages for this site, and footer pages.
    Get all this info and return a dictionary ready to pass to render_to_response. Convenience method
    to save typing.
 
    """

    try:
        site = getSite(site_short_name)
        pages = getPages(site_short_name)
        metafooterpages = getPages(settings.MAIN_PROJECT_NAME)


    except ComicSite.DoesNotExist:
        # Site is not known, default to main project.      
        site = getSite(settings.MAIN_PROJECT_NAME)
        metafooterpages = getPages(settings.MAIN_PROJECT_NAME)
        pages = []  # don't show any pages here

    return [site, pages, metafooterpages]


def renderTags(request, p, recursecount=0):
    """ render page contents using django template system
    This makes it possible to use tags like '{% dataset %}' in page content.
    If a rendered tag results in another tag, this can be rendered recursively
    as long as recurse limit is not exceeded.
    
    """
    recurselimit = 2

    try:
        t = Template("{% load comic_templatetags %}" + p.html)
    except TemplateSyntaxError as e:
        # when page contents cannot be rendered, just display raw contents and include error message on page
        errormsg = "<span class=\"pageError\"> Error rendering template: %s </span>" % e
        pagecontents = p.html + errormsg
        return pagecontents

    t = escape_verbatim_node_contents(t)

    # pass page to context here to be able to render tags based on which page does the rendering
    pagecontents = t.render(ComicSiteRequestContext(request, p))

    if "{%" in pagecontents or "{{" in pagecontents:  # if rendered tags results in another tag, try to render this as well
        if recursecount < recurselimit:
            p2 = copy_page(p)
            p2.html = pagecontents
            return renderTags(request, p2, recursecount + 1)
        else:
            # when page contents cannot be rendered, just display raw contents and include error message on page
            errormsg = "<span class=\"pageError\"> Error rendering template: rendering recursed further than" + str(
                recurselimit) + " </span>"
            pagecontents = p.html + errormsg

    return pagecontents


def escape_verbatim_node_contents(template):
    """ Page contents are possibly doing multiple passes through rendering. This
    means the {% verbatim %} tag will usually now work as expected because its 
    contents are rendered verbatim and then rendered again, actually evaluating
    whatever the verbatim content should be. This method puts additional 
    {% verbatim %} tags around any {% verbatim %} node found. 
    
    This crude method is a lot easier than defining a custom render()
    method  
    """

    for node in template.nodelist:
        if type(node) == VerbatimNode:
            node.content = node.content.replace("%", "&#37")

    return template


def permissionMessage(request, site, p):
    if request.user.is_authenticated():
        msg = """ <div class="system_message">
                <h2> Restricted page</h2>
                  This page can only be viewed by participants of this project to view this page please make sure of the following:
                  <ul>
                      <li>First, log in to {0} by using the 'Sign in' button at the top right.</li>
                      <li>Second, you need to join / register with the specific project you are interested in as a participant. 
                      The link to do this is provided by the project organizers on the project website.</li>
                  </ul>
                  <div>
              """.format(settings.MAIN_PROJECT_NAME)
        title = p.title
    else:
        msg = "The page '" + p.title + "' can only be viewed by registered users. Please sign in to view this page."
        title = p.title
    page = ErrorPage(comicsite=site, title=title, html=msg)
    currentpage = page
    return currentpage


# TODO: could a decorator be better then all these ..IfAllowed pages?
def getRenderedPageIfAllowed(page_or_page_title, request, site):
    """ check permissions and render tags in page. If string title is given page is looked for 
        return nice message if not allowed to view"""

    if isinstance(page_or_page_title, bytes):
        page_or_page_title = page_or_page_title.decode()

    if isinstance(page_or_page_title, str):
        page_title = page_or_page_title
        try:
            p = Page.objects.get(comicsite__short_name=site.short_name,
                                 title=page_title)
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


def get_data_folder_path(project_name):
    """ Returns physical base path to the root of the folder where all files for
    this project are kept """
    return path.join(settings.MEDIA_ROOT, project_name)


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

    site_short_name = settings.MAIN_PROJECT_NAME

    if ComicSite.objects.filter(short_name=site_short_name).count() == 0:
        link = reverse('challenge_create')
        link = link + "?short_name=%s" % site_short_name
        link_html = create_HTML_a(link,
                                  "Create project '%s'" % site_short_name)
        html = """I'm trying to show the first page for main project '%s' here,
        but '%s' does not exist. %s.""" % (site_short_name,
                                           site_short_name,
                                           link_html)
        p = create_temp_page(title="no_pages_found", html=html)
        return render(
            request,
            'temppage.html',
            {
                'site': p.comicsite,
                'currentpage': p,
            },
        )

    pages = getPages(site_short_name)

    if pages.count() == 0:

        link = reverse('admin:comicmodels_comicsite_changelist')
        link_html = create_HTML_a(link, "admin interface")

        html = """I'm trying to show the first page for main project '%s' here,
        but '%s' contains no pages. Please add
        some in the %s.""" % (site_short_name,
                              site_short_name,
                              link_html)

        p = create_temp_page(title="no_pages_found", html=html)
        return render(
            request,
            'temppage.html',
            {
                'site': p.comicsite,
                'currentpage': p,
            },
        )

    elif page_title == "":
        # if no page title is given, just use the first page found
        p = pages[0]
        p.html = renderTags(request, p)

    else:
        try:
            p = Page.objects.get(comicsite__short_name=site_short_name,
                                 title=page_title)
        except Page.DoesNotExist:
            raise Http404

    p.html = renderTags(request, p)

    # render page contents using django template system
    # This makes it possible to use tags like '{% dataset %}' in page

    # to display pages from main project at the very bottom of the site as
    # general links
    metafooterpages = getPages(settings.MAIN_PROJECT_NAME)

    return render(
        request,
        'mainpage.html',
        {
            'site': p.comicsite,
            'currentpage': p,
            "pages": pages,
            "metafooterpages": metafooterpages,
        },
    )


# ======================================== not called directly from urls.py =========================================

def getSite(site_short_name):
    project = ComicSite.objects.get(short_name=site_short_name)
    return project


def getPages(site_short_name):
    """ get all pages of the given site from db"""
    try:
        pages = Page.objects.filter(comicsite__short_name=site_short_name)
    except Page.DoesNotExist:
        raise Http404("Page '%s' not found" % site_short_name)
    return pages


# trying to follow pep 0008 here, finally.
def site_exists(site_short_name):
    try:
        site = ComicSite.objects.get(short_name=site_short_name)
        return True
    except ComicSite.DoesNotExist:
        return False


def comic_site_to_grand_challenge_html(comic_site, link=""):
    """ Return an html overview of the given ComicSite, in the same style as 
    listings on grand_challenge.org 
    
    """

    if link == "":
        link = reverse('challenge-homepage', args=[comic_site.short_name])

    html = create_HTML_a(link, comic_site.short_name)

    if comic_site.description != "":
        html += " - " + comic_site.description

    img_html = create_HTML_a_img(link, comic_site.logo)

    html = "<table class=\"upcoming comic\"><tbody><tr valign=\"top\"><td><span class=\"plainlinks\" id=\"" + comic_site.short_name + "\"><a href=\"" + link + "\"><img alt=\"\" src=\"" + comic_site.logo + "\" height=\"100\" border=\"0\" width=\"100\"></td></a></span><td>" + comic_site.description + "<br>Website: <a class=\"external free\" title=\"" + comic_site.short_name + "\"href=\"" + link + "\">" + link + "</a><br>Event: <a class=\"external text\" title=\"none\" href=\"\">MICCAI, September 22, 2013</a></td></tr></tbody></table>"

    return html


def create_HTML_a(link_url, link_text):
    return "<a href=\"" + link_url + "\">" + link_text + "</a>"


def create_HTML_a_img(link_url, image_url):
    """ create a linked image """
    img = "<img src=\"" + image_url + "\">"
    linked_image = create_HTML_a(link_url, img)
    return linked_image


def copy_page(page):
    return Page(comicsite=page.comicsite, title=page.title, html=page.html)


def create_temp_page(title="temp_page", html=""):
    """ Create a quick mockup page which you can show, without needing to read 
    anything from database
    
    """
    site = ComicSite()  # any page requires a site, create on the fly here.
    site.short_name = "Temp"
    site.name = "Temporary page"
    site.skin = ""

    return Page(comicsite=site, title=title, html=html)
