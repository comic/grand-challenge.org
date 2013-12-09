'''
Created on Jun 18, 2012

Testing views. Each of these views is referenced in urls.py 

@author: Sjoerd
'''
import pdb
import mimetypes
import logging
 


from os import path
from django.conf import settings
from django.contrib.admin.options import ModelAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import ImproperlyConfigured
from django.core.files import File
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.http import HttpResponse,Http404,HttpResponseForbidden
from django.shortcuts import render_to_response,get_object_or_404
from django.template import RequestContext,Context,Template,TemplateSyntaxError

from userena import views as userena_views

from comicmodels.models import ComicSite,Page,ErrorPage,DropboxFolder,ComicSiteModel,RegistrationRequest
from comicsite.admin import ComicSiteAdmin
from comicsite.template.context import ComicSiteRequestContext
from comicsite.models import ComicSiteException

from filetransfers.api import serve_file
from filetransfers.views import download_handler_file
from dataproviders import FileSystemDataProvider


def index(request):
    return  HttpResponse("ComicSite index page.",context_instance=RequestContext(request))




def _register(request, site_short_name):
    """ Register the current user for given comicsite """
   
    #TODO: check whether user is allowed to register, maybe wait for verification,
    #send email to admins of new registration
    
    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)
    
    if site.require_participant_review:
        currentpage = _register_after_approval(request, site)
    else:
        currentpage = _register_directly(request, site)
    
    return render_to_response('page.html', {'site': site, 'currentpage': currentpage, "pages":pages},context_instance=RequestContext(request))
    

def _register_directly(request, site):
    
    title = "registration_successful"
    display_title = "registration successful"
    if request.user.is_authenticated():
        participantsgroup = Group.objects.get(name=site.participants_group_name())
        request.user.groups.add(participantsgroup)
        html = "<p> You are now registered to " + site.short_name + "<p>"
    else:
        html = "you need to be logged in to use this url"
    
    currentpage = Page(comicsite=site, title=title, display_title=display_title, html=html)
    return currentpage


def _register_after_approval(request, project):
    
    title = "registration requested"
    display_title = "registration requested"
    if request.user.is_authenticated():
        
        pending = RegistrationRequest.objects.get_pending_registration_requests(request.user,project)
                
        if pending:            
            html = pending[0].status_to_string()
            pass #do not add another request
        else:
            participantsgroup = Group.objects.get(name=project.participants_group_name())
            reg_request = RegistrationRequest()
            reg_request.project = project
            reg_request.user = request.user
            reg_request.save()
            #request.user.groups.add(participantsgroup)
            html = "<p> A registration request has been sent to the " + project.short_name + " organizers.You will receive an email when your request has been reviewed<p>"
                
    else:
        html = "you need to be logged in to use this url"
    
    currentpage = Page(comicsite=project, title=title, display_title=display_title, html=html)
    return currentpage


def site(request, site_short_name):    
   
    #TODO: Doing two calls to getSite here. (second one in site_get_standard_vars)
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
        page = ErrorPage(comicsite=site,title="no_pages_found",html="No pages found for this site. Please log in and use the admin button to add pages.")
        currentpage = page    
    else:
        currentpage = pages[0]
            
    currentpage = getRenderedPageIfAllowed(currentpage,request,site)
    #return render_to_response('page.html', {'site': site, 'currentpage': currentpage, "pages":pages, "metafooterpages":metafooterpages},context_instance=RequestContext(request))
    return render_to_response('page.html', {'site': site, 'currentpage': currentpage, "pages":pages},context_instance=RequestContext(request))

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
        pages = [] #don't show any pages here
            
    return [site, pages, metafooterpages]
        
def concatdicts(d1,d2):
    return dict(d1, **d2)
    

def renderTags(request, p, recursecount=0):
    """ render page contents using django template system
    This makes it possible to use tags like '{% dataset %}' in page content.
    If a rendered tag results in another tag, this can be rendered recursively
    as long as recurse limit is not exceeded.
    
    """
    recurselimit = 2
    rendererror = ""
    
    
    try:
        t = Template("{% load comic_templatetags %}" + p.html)
    except TemplateSyntaxError as e:
        rendererror = e.message
    if (rendererror):
        # when page contents cannot be rendered, just display raw contents and include error message on page
        errormsg = "<span class=\"pageError\"> Error rendering template: " + rendererror + " </span>"
        pagecontents = p.html + errormsg
    else:
                
        #pass page to context here to be able to render tags based on which page does the rendering
        
        pagecontents = t.render(ComicSiteRequestContext(request,p))            
                
        if "{%" in pagecontents or "{{" in pagecontents: #if rendered tags results in another tag, try to render this as well
            if recursecount < recurselimit :                
                p2 = copy_page(p) 
                p2.html = pagecontents
                return renderTags(request,p2,recursecount+1)
            else:
                # when page contents cannot be rendered, just display raw contents and include error message on page
                errormsg = "<span class=\"pageError\"> Error rendering template: rendering recursed further than" + str(recurselimit) + " </span>"
                pagecontents = p.html + errormsg
         
        
    return pagecontents



def permissionMessage(request, site, p):
    if request.user.is_authenticated():
        msg = "You do not have permission to view page '" + p.title + "'. If you feel this is an error, please contact the project administrators"
        title = p.title
    else:
        msg = "The page '" + p.title + "' can only be viewed by registered users. Sign in to view this page."
        title = p.title
    page = ErrorPage(comicsite=site, title=title, html=msg)
    currentpage = page
    return currentpage

    
#TODO: could a decorator be better then all these ..IfAllowed pages?
def getRenderedPageIfAllowed(page_or_page_title,request,site):
    """ check permissions and render tags in page. If string title is given page is looked for 
        return nice message if not allowed to view"""
        
    if isinstance(page_or_page_title,unicode) or isinstance(page_or_page_title,str):
        page_title = page_or_page_title
        try:
            p = Page.objects.get(comicsite__short_name=site.short_name, title=page_title)
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

    
def getPageSourceIfAllowed(page_title,request,site):
    """ check permissions and render tags in page. If string title is given page is looked for 
        return nice message if not allowed to view"""
    
    try:
        p = Page.objects.get(comicsite__short_name=site.short_name, title=page_title)
    except Page.DoesNotExist:
        raise Http404
        
    if p.can_be_viewed_by(request.user):        
        currentpage = p    

    else:         
        currentpage = permissionMessage(request, site, p)
            
    return currentpage



def projectlinks(request):
    """ Show an overview of all projects registered at comic or listed at
    grand-challenge.org 
    
    """    
    response =  render_to_response('projectlinks.html', context_instance=RequestContext(request))
    return response
    


def page(request, site_short_name, page_title):
    """ show a single page on a site """
    
    
    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)
    currentpage = getRenderedPageIfAllowed(page_title,request,site)
    response =  render_to_response('page.html',
                                           {'currentpage': currentpage},
                                           context_instance=RequestContext(request))
    
    # TODO: THis has code smell. If page has to be checked like this, is it 
    # ok to use a page object for error messages?
    if hasattr(currentpage,"is_error_page"):
        if currentpage.is_error_page == True:
            response.status_code = "403"
             
    return response



def pagesource(request, site_short_name, page_title):
    """ show the source html + tags of a a single page on a site 
    
    """
    
    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)    
    currentpage = getPageSourceIfAllowed(page_title,request,site)
        
    return render_to_response('pagesource.html', {'site': site, 'currentpage': currentpage, "pages":pages, 
                                            "metafooterpages":metafooterpages},
                                            context_instance=RequestContext(request))


def errorpage(request,site_short_name,page_title,message):
    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)    
    page = ErrorPage(comicsite=site, title=page_title, html=message)
    return render_to_response('page.html', {'site': site, 'currentpage': page, "pages":pages, 
                                            "metafooterpages":metafooterpages},
                                            context_instance=RequestContext(request))



def insertedpage(request, site_short_name, page_title, dropboxpath):
    """ show contents of a file from the local dropbox folder for this project
     
    """
    
    (mimetype,encoding) = mimetypes.guess_type(dropboxpath)
            

    if mimetype == None:
        mimetype = "NoneType"  #make the next statement not crash on non-existant mimetype
        
    if mimetype.startswith("image"):
        return inserted_file(request, site_short_name, dropboxpath)
    
    if mimetype == "application/pdf" or mimetype == "application/zip":
        return inserted_file(request, site_short_name, dropboxpath)
        
        #filename = path.join(settings.DROPBOX_ROOT,site_short_name,dropboxpath)
        #return download_handler_file(request,filename)        
        #return offerdownload
    
    
    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)
        
    p = get_object_or_404(Page,comicsite__short_name=site.short_name, title=page_title)
    
    baselink = reverse('comicsite.views.page', kwargs = {'site_short_name':p.comicsite.short_name, 'page_title':p.title})
    
    msg = "<div class=\"breadcrumbtrail\"> Displaying '"+dropboxpath+"' from local dropboxfolder, originally linked from\
           page <a href=\""+baselink+"\">"+p.title+"</a> </div>"
    p.html = "{% insert_file "+dropboxpath+" %} <br/><br/>" + msg
    
    currentpage = getRenderedPageIfAllowed(p,request,site)
    
    
    return render_to_response('dropboxpage.html', {'site': site, 'currentpage': currentpage, "pages":pages, 
                                            "metafooterpages":metafooterpages},
                                            context_instance=RequestContext(request))

    
def inserted_file(request, site_short_name, filepath=""):
    """ Get image from local dropbox and serve. 
    
    
    """        
    
    from filetransfers.views import can_access
    
    filename = path.join(settings.DROPBOX_ROOT,site_short_name,filepath)
    
    # can this location be served regularly (e.g. it is in public folder)?
    serve_allowed = can_access(request.user,filepath,site_short_name)
    
    # if not, linking to anywhere should be possible because it is convenient
    # and the security risk is not too great. TODO (is it not?)     
    if not serve_allowed:
        serve_allowed = can_access(request.user,          
                  filepath,
                  site_short_name,          
                  override_permission=ComicSiteModel.REGISTERED_ONLY)
    
    if serve_allowed:
        try:            
            file = open(filename,"rb")        
        except Exception:
            raise Http404
    
        django_file = File(file)
        return serve_file(request,django_file)
    
    else:
        return HttpResponseForbidden("This file is not available without "
                                    "credentials")
        


def dropboxpage(request, site_short_name, page_title, dropboxname, dropboxpath):
    """ show contents of a file from dropbox account as page """
    
    (mimetype,encoding) = mimetypes.guess_type(dropboxpath)
    if mimetype.startswith("image"):
        return dropboximage(request, site_short_name, page_title,dropboxname, dropboxpath)
        
    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)
        
    p = get_object_or_404(Page,comicsite__short_name=site.short_name, title=page_title)
    
    baselink = reverse('comicsite.views.page', kwargs = {'site_short_name':p.comicsite.short_name, 'page_title':p.title})
    
    msg = "<div class=\"breadcrumbtrail\"> Displaying '"+dropboxpath+"' from dropboxfolder '"+dropboxname+"', originally linked from\
           page <a href=\""+baselink+"\">"+p.title+"</a> </div>"
    p.html = "{% dropbox title:"+dropboxname+" file:"+dropboxpath+" %} <br/><br/>" + msg

    currentpage = getRenderedPageIfAllowed(p,request,site)

        
    return render_to_response('dropboxpage.html', {'site': site, 'currentpage': currentpage, "pages":pages, 
                                            "metafooterpages":metafooterpages},
                                            context_instance=RequestContext(request))


def dropboximage(request, site_short_name, page_title,dropboxname,dropboxpath=""):
    """ Get image from dropbox and pipe through django. 
    Sjoerd: This method is probably very inefficient, however it works. optimize later > maybe get temp public link
    from dropbox api and let dropbox serve, or else do some cashing. Cut out the routing through django.
    """
    df = get_object_or_404(DropboxFolder,title=dropboxname)    
    provider = df.get_dropbox_data_provider()
    
    (mimetype,encoding) = mimetypes.guess_type(dropboxpath)
    response = HttpResponse(provider.read(dropboxpath), content_type=mimetype)
    
    return response
    
    


def comicmain(request, page_title=""):
    """ show content as main page item. Loads pages from the main project """
        
    site_short_name = settings.MAIN_PROJECT_NAME
    
    if ComicSite.objects.filter(short_name=site_short_name).count() == 0:
        link = reverse('admin:comicmodels_comicsite_add')
        link = link + "?short_name=%s" % site_short_name
        link_html = create_HTML_a(link,"Create project '%s'" % site_short_name)
        html = """I'm trying to show the first page for main project '%s' here,
        but '%s' does not exist. %s.""" % (site_short_name,
              site_short_name,
              link_html)
        p = create_temp_page(title="no_pages_found",html=html)
        return render_to_response('temppage.html',
                                  {'site': p.comicsite,
                                   'currentpage': p},
                                  context_instance=RequestContext(request))

            
    pages = getPages(site_short_name)
    
    if pages.count() == 0:
                
        link = reverse('admin:comicmodels_comicsite_changelist')
        link_html = create_HTML_a(link,"admin interface")
        
        html = """I'm trying to show the first page for main project '%s' here,
        but '%s' contains no pages. Please add
        some in the %s.""" % (site_short_name,
                              site_short_name,
                              link_html)
                               
        p = create_temp_page(title="no_pages_found",html=html)
        return render_to_response('temppage.html',
                                  {'site': p.comicsite,
                                   'currentpage': p},                                                                    
                                  context_instance=RequestContext(request))
        
    elif page_title=="":
        #if no page title is given, just use the first page found            
            p = pages[0]
            p.html = renderTags(request, p)        
                    
    else:     
        try:            
            p = Page.objects.get(comicsite__short_name=site_short_name, title=page_title)            
        except Page.DoesNotExist:                
            raise Http404
    
    
    p.html = renderTags(request, p)
    
    # render page contents using django template system
    # This makes it possible to use tags like '{% dataset %}' in page
    
    # to display pages from main project at the very bottom of the site as
    # general links
    metafooterpages = getPages(settings.MAIN_PROJECT_NAME)
    
    return render_to_response('mainpage.html',
                              {'site': p.comicsite,
                               'currentpage': p,
                               "pages":pages,
                               "metafooterpages":metafooterpages},
                              context_instance=RequestContext(request))

                
    
def dataPage(request):
    """ test function for data provider. Just get some files from provider and
    show them as list
    
    """    
    path = r"D:\userdata\Sjoerd\Aptana Studio 3 Workspace\comic\comic-django"\
             "\django\static\files"
    dp = FileSystemDataProvider.FileSystemDataProvider(path)
    images = dp.getImages()
    
    htmlOut = "available files:"+", ".join(images)
    #p = createTestPage(html=htmlOut)
    p = create_temp_page(html=htmlOut)
    
    pages = [p]
    
    return render_to_response('testpage.html',
                              {'site': p.comicsite,
                               'currentpage': p,
                               "pages":pages }
                              ,context_instance=RequestContext(request))

# ======================================== not called directly from urls.py =========================================

def getSite(site_short_name):
    project = ComicSite.objects.get(short_name=site_short_name)                       
    return project
    
def getPages(site_short_name):
    """ get all pages of the given site from db"""    
    try:
        pages = Page.objects.filter(comicsite__short_name=site_short_name)
    except Page.DoesNotExist:                
        raise Http404("Page '%s' not found" %site_short_name)
    return pages

# trying to follow pep 0008 here, finally.
def site_exists(site_short_name):
    try:
        site = ComicSite.objects.get(short_name=site_short_name)
        return True
    except ComicSite.DoesNotExist:                
        return False


def comic_site_to_grand_challenge_html(comic_site,link=""):
     """ Return an html overview of the given ComicSite, in the same style as 
     listings on grand_challenge.org 
     
     """
     
     if link == "":
         link = reverse('comicsite.views.site', args=[comic_site.short_name])
              
     html = create_HTML_a(link,comic_site.short_name)
     
     if comic_site.description !="":
         html += " - " + comic_site.description
         
     img_html = create_HTML_a_img(link,comic_site.logo)
     
     html = "<table class=\"upcoming comic\"><tbody><tr valign=\"top\"><td><span class=\"plainlinks\" id=\""+comic_site.short_name+"\"><a href=\""+link+"\"><img alt=\"\" src=\""+comic_site.logo+"\" height=\"100\" border=\"0\" width=\"100\"></td></a></span><td>"+comic_site.description+"<br>Website: <a class=\"external free\" title=\""+comic_site.short_name+"\"href=\""+link+"\">"+link+"</a><br>Event: <a class=\"external text\" title=\"none\" href=\"\">MICCAI, September 22, 2013</a></td></tr></tbody></table>"
          
          
     return html
 
 
def comic_site_to_html(comic_site,link=""):
     """ Return an html overview of the given ComicSite """
     
     if link == "":
         link = reverse('comicsite.views.site', args=[comic_site.short_name])
     
     html = create_HTML_a(link,comic_site.short_name)
     
     if comic_site.description !="":
         html += " - " + comic_site.description
     
     
     image_link = reverse('project_serve_file', args=[comic_site.short_name,comic_site.logo])     
    
     img_html = create_HTML_a_img(link,image_link)
     
     html = "<table><tr valign=\"top\" ><td class = \"thumb\">" + img_html +"</td><td class = \"description\">"+ html + "</td></tr></table>"
     
     html = "<div class = \"comicSiteSummary\">" + html + "</div>"
     return html

    
def create_HTML_a(link_url,link_text):
    return "<a href=\"" + link_url + "\">" +  link_text + "</a>"


def create_HTML_a_img(link_url,image_url):
    """ create a linked image """
    img = "<img src=\"" + image_url + "\">"
    linked_image = create_HTML_a(link_url,img)    
    return linked_image

def copy_page(page):
    return Page(comicsite=page.comicsite,title=page.title,html=page.html)


def create_temp_page(title="temp_page",html=""):
    """ Create a quick mockup page which you can show, without needing to read 
    anything from database
    
    """        
    site = ComicSite() #any page requires a site, create on the fly here.
    site.short_name = "Temp"
    site.name = "Temporary page"
    site.skin = ""
        
    return Page(comicsite=site,title=title,html=html)

#====================== Wrapping profiles views ================================
# Profiles views shoudld be viewable in each project. Each view needs a
# site_short_name or similar param. Therefore all needed views are wrapped here.
# TODO: is there no less repetitive way of wrapping?

def get_extra_context(site_short_name):
    """ reduces duplication in signin signup methods below.
    
    """
    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)
    if site.short_name.lower() == settings.MAIN_PROJECT_NAME.lower():
        pages = []
    extra_context = {'site':site, "pages":pages}
    return extra_context

def signin(request, site_short_name, extra_context=None):        
    """ change userena signup so it shows the banner and layout of current
    project. 
    
    Also do not show any pages for main project, because logging
    in here should feel like a 'general' login and not like logging in to a
    project 
         
    """
    extra_context = get_extra_context(site_short_name)    
    # signup_form, template_name, success_url, extra_context    
    response = userena_views.signin(request=request, extra_context=extra_context)
    return response

def signup(request, site_short_name, extra_context=None,**kwargs):            
    extra_context = get_extra_context(site_short_name)
    # signup_form, template_name, success_url, extra_context    
    success = reverse("comicsite_signup_complete",kwargs={"site_short_name":site_short_name})
    response = userena_views.signup(request=request,
                                    extra_context=extra_context,
                                    success_url=success,
                                    **kwargs)
    return response

def signup_complete(request, site_short_name,):        
    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)
    
    # currentpage needed to make templates not trip
    currentpage= Page(comicsite=site,title="Signup_almost_complete",html="")        
    response =  render_to_response('userena/signup_complete.html',
                                           {'site': site,                                        
                                            "pages":pages,
                                            "currentpage":currentpage,
                                            "metafooterpages":metafooterpages},
                                           context_instance=RequestContext(request))
    
    return response


    
# ======================================================  debug and test ==================================================

 
def send_email(request):
    """Test email sending"""
        
    adress = 'w.s.kerkstra@gmail.com' 
    title = 'Your email setting are ok for sending'
    message = 'Just checking the sending of email using DJANGO. If you read this things are properly configured'
    
    password = ""
    if request.GET.has_key("pass"):
        password = request.GET['pass']
    
    #only set password if bots really make this a problem
    if True: #password == "one0nine":
        send_mail(title, 'Here is the message.', 'test@comicframework.org',
                  [adress], fail_silently=False)
        text="Sent test email titled '" + title + "' to email adress '"+ adress +"'"
        
    return HttpResponse(text);

def test_logging(request):    
    logger = logging.getLogger("django")
    
    logger.critical("This is critical")
    logger.error("This is error")
    logger.warning("This is warning")
    logger.info("This is info")
    logger.debug("This is debug")

    return HttpResponse("logged")

def throw_exception(request):
    """ Test handling of exceptions
    
    """
    raise ComicSiteException("An exception thrown to test exception handling")

def throw_http404(request):
    """ Test handling of exceptions
    
    """
    raise Http404("A Http404 to test exception handling")



    

def givePageHTML(page):
    return "<h1>%s</h1> <p>%s</p>" %(page.title ,page.html)