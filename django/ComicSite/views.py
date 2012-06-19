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


def site(request, site_id):
    """ show a single COMIC site, default start page """
    
    try:
        s = ComicSite.objects.get(pk=site_id)
    except ComicSite.DoesNotExist:                
        raise Http404            
    
    pages = getPages(site_id)
                    
    return render_to_response('site.html', {'site': s, 'pages': pages})
    


def page(request, site_id, page_title):
    """ show a single page on a site """
    
    try:
        p = Page.objects.get(ComicSite__pk=site_id, title=page_title)
    except Page.DoesNotExist:                
        raise Http404
    pages = getPages(site_id)
    
    return render_to_response('page.html', {'site': p.ComicSite, 'page': p, "pages":pages })
                
    #return HttpResponse(givePageHTML(p))
    

def getPages(site_id):
    """ get all pages of the given site from db"""
    try:
        pages = Page.objects.filter(ComicSite__pk=site_id)
    except Page.DoesNotExist:                
        raise Http404
    return pages

    

def givePageHTML(page):
    return "<h1>%s</h1> <p>%s</p>" %(page.title ,page.html)