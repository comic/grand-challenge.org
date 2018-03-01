import mimetypes
from itertools import chain
from os import path

from auth_mixins import LoginRequiredMixin
from django.conf import settings
from django.core.files import File
from django.core.files.storage import DefaultStorage
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.shortcuts import render_to_response, get_object_or_404
from django.template import Template, TemplateSyntaxError
from django.template.defaulttags import VerbatimNode
from django.views.generic import TemplateView

from comicmodels.models import (
    ComicSite,
    Page,
    ErrorPage,
    ComicSiteModel,
    RegistrationRequest,
)
from comicsite.core.urlresolvers import reverse
from comicsite.template.context import (
    ComicSiteRequestContext,
    CurrentAppRequestContext,
)
from filetransfers.api import serve_file


def index(request):
    return HttpResponse("ComicSite index page.",
                        context_instance=CurrentAppRequestContext(request))


class ParticipantRegistration(LoginRequiredMixin, TemplateView):
    template_name = 'participant_registration.html'

def _register(request, site_short_name):
    """ Register the current user for given comicsite """

    # TODO: check whether user is allowed to register, maybe wait for verification,
    # send email to admins of new registration

    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)
    if request.user.is_authenticated():
        if site.require_participant_review:
            currentpage = _register_after_approval(request, site)
        else:
            currentpage = _register_directly(request, site)

    else:
        if "user_just_registered" in request.GET:
            # show message to use activation mail first, then refresh the page
            html = """<h2> Please activate your account </h2> 
            <p>An activation link has been sent to the email adress you provided.
            Please use this link to activate your account.</p> 
            
            After activating your account, click <a href="{0}">here to continue</a>  
            """.format("")

            currentpage = Page(comicsite=site, title="activate_your_account",
                               display_title="activate your account",
                               html=html)
        else:
            html = "you need to be logged in to use this url"
            currentpage = Page(comicsite=site, title="please_log_in",
                               display_title="Please log in", html=html)

    return render_to_response('page.html',
                              {'site': site, 'currentpage': currentpage,
                               "pages": pages},
                              context_instance=CurrentAppRequestContext(
                                  request))


def _register_directly(request, project):
    if request.user.is_authenticated():
        project.add_participant(request.user)
        title = "registration_successful"
        display_title = "registration successful"
        html = "<p> You are now registered for " + project.short_name + "<p>"
    else:
        title = "registration_unsuccessful"
        display_title = "registration unsuccessful"
        html = "<p><b>ERROR:</b>You need to be signed in to register<p>"

    currentpage = Page(comicsite=project, title=title,
                       display_title=display_title, html=html)
    return currentpage


def _register_after_approval(request, project):
    title = "registration requested"
    display_title = "registration requested"

    pending = RegistrationRequest.objects.get_pending_registration_requests(
        request.user, project)
    accepted = RegistrationRequest.objects.get_accepted_registration_requests(
        request.user, project)

    pending_or_accepted = list(chain(pending, accepted))

    if pending_or_accepted:
        html = pending_or_accepted[0].status_to_string()
        pass  # do not add another request
    else:
        reg_request = RegistrationRequest()
        reg_request.project = project
        reg_request.user = request.user
        reg_request.save()
        from comicsite.models import \
            send_participation_request_notification_email
        send_participation_request_notification_email(request, reg_request)

        html = "<p> A participation request has been sent to the " + project.short_name + " organizers. You will receive an email when your request has been reviewed<p>"

    currentpage = Page(comicsite=project, title=title,
                       display_title=display_title, html=html)
    return currentpage


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
    # return render_to_response('page.html', {'site': site, 'currentpage': currentpage, "pages":pages, "metafooterpages":metafooterpages},context_instance=CurrentAppRequestContext(request))
    return render_to_response('page.html',
                              {'site': site, 'currentpage': currentpage,
                               "pages": pages},
                              context_instance=CurrentAppRequestContext(
                                  request))


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


def page(request, site_short_name, page_title):
    """ show a single page on a site """

    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)
    currentpage = getRenderedPageIfAllowed(page_title, request, site)
    response = render_to_response('page.html',
                                  {'currentpage': currentpage},
                                  context_instance=CurrentAppRequestContext(
                                      request))

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

    return render_to_response('dropboxpage.html',
                              {'site': site, 'currentpage': currentpage,
                               "pages": pages,
                               "metafooterpages": metafooterpages},
                              context_instance=CurrentAppRequestContext(
                                  request))


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
        return render_to_response('temppage.html',
                                  {'site': p.comicsite,
                                   'currentpage': p},
                                  context_instance=CurrentAppRequestContext(
                                      request))

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
        return render_to_response('temppage.html',
                                  {'site': p.comicsite,
                                   'currentpage': p},
                                  context_instance=CurrentAppRequestContext(
                                      request))

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

    context = CurrentAppRequestContext(request)
    # context.current_app = "VESSEL12admin"

    return render_to_response('mainpage.html',
                              {'site': p.comicsite,
                               'currentpage': p,
                               "pages": pages,
                               "metafooterpages": metafooterpages},
                              context_instance=context)


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
