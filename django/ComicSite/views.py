'''
Created on Jun 18, 2012

Testing views. Each of these views is referenced in urls.py 

@author: Sjoerd
'''

from django.http import HttpResponse
from ComicSite.models import ComicSite,Page
from django.http import Http404
from django.shortcuts import render_to_response

def index(request):
    return  HttpResponse("ComicSite index page.")


def site(request, site_name):
    """ show a single COMIC site, default start page """
    #TODO: Is it bad to use site name here, which is not the specified key?
    site = getSite(site_name)
                    
    pages = getPages(site_name)
                    
    return render_to_response('site.html', {'site': site, 'pages': pages})
    

def page(request, site_name, page_title):
    """ show a single page on a site """
    
    try:
        p = Page.objects.get(ComicSite__name=site_name, title=page_title)
    except Page.DoesNotExist:                
        raise Http404
    pages = getPages(site_name)
    
    return render_to_response('page.html', {'site': p.ComicSite, 'page': p, "pages":pages })
                
    #return HttpResponse(givePageHTML(p))
    



def getSite(site_name):
    try:
        site = ComicSite.objects.get(name=site_name)
    except ComicSite.DoesNotExist:                
        raise Http404   
    return site  
    
    

def getPages(site_name):
    """ get all pages of the given site from db"""
    try:
        pages = Page.objects.filter(ComicSite__name=site_name)
    except Page.DoesNotExist:                
        raise Http404
    return pages

    

def givePageHTML(page):
    return "<h1>%s</h1> <p>%s</p>" %(page.title ,page.html)