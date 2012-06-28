'''
Created on Jun 18, 2012

Testing views. Each of these views is referenced in urls.py 

@author: Sjoerd
'''

from django.http import HttpResponse
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext

from comicsite.models import ComicSite,Page
from dataproviders import FileSystemDataProvider


def index(request):
    return  HttpResponse("ComicSite index page.",context_instance=RequestContext(request))


def site(request, site_short_name):
    """ show a single COMIC site, default start page """
    #TODO: Is it bad to use site name here, which is not the specified key?
    site = getSite(site_short_name)
                    
    pages = getPages(site_short_name)
                    
    return render_to_response('site.html', {'site': site, 'pages': pages},context_instance=RequestContext(request))
    

def page(request, site_short_name, page_title):
    """ show a single page on a site """
    
    try:
        p = Page.objects.get(ComicSite__short_name=site_short_name, title=page_title)
    except Page.DoesNotExist:                
        raise Http404
    pages = getPages(site_short_name)
    
    return render_to_response('page.html', {'site': p.ComicSite, 'page': p, "pages":pages },context_instance=RequestContext(request))
                
    #return HttpResponse(givePageHTML(p))
    

def dataPage(request):
    """ test function for data provider"""
    #= r"D:\userdata\Sjoerd\Aptana Studio 3 Workspace\comic-django\django\static\files"
    
    path = r"D:\userdata\Sjoerd\Aptana Studio 3 Workspace\comic-django\django\static\files"
    dp = FileSystemDataProvider.FileSystemDataProvider(path)
    images = dp.getImages()
    
    htmlOut = "available files:"+", ".join(images)
    p = createTestPage(html=htmlOut)
    pages = [p]
    
    return render_to_response('page.html', {'site': p.ComicSite, 'page': p, "pages":pages },context_instance=RequestContext(request))

# ======================================== not called directly from urls.py =========================================

def getSite(site_short_name):
    try:
        site = ComicSite.objects.get(short_name=site_short_name)
    except ComicSite.DoesNotExist:                
        raise Http404   
    return site  
    
    

def getPages(site_short_name):
    """ get all pages of the given site from db"""
    try:
        pages = Page.objects.filter(ComicSite__short_name=site_short_name)
    except Page.DoesNotExist:                
        raise Http404
    return pages

    
# ======================================================  debug and test ==================================================
def createTestPage(title="testPage",html=""):
    """ Create a quick mockup on the ComicSite 'Test'"""
    try: 
        site = getSite("test")
    except Http404:
        raise ComicSite.DoesNotExist("To show a testpage you have to have a ComicSite called 'test' (called by /test)..")
    
    return Page(ComicSite=site,title=title,html=html)
    

def givePageHTML(page):
    return "<h1>%s</h1> <p>%s</p>" %(page.title ,page.html)