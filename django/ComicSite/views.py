'''
Created on Jun 18, 2012

Testing views. Each of these views is referenced in urls.py 

@author: Sjoerd
'''

from django.http import HttpResponse
from ComicSite.models import ComicSite,Page
from django.http import Http404

def index(request):
    return  HttpResponse("ComicSite index page.")


def site(request, site_id):
    
    try:
        s = ComicSite.objects.get(pk=site_id)
    except ComicSite.DoesNotExist:                
        raise Http404            
    
    pages = Page.objects.filter(ComicSite=s)
    pageHTML = ""
    for page in pages:
        pageHTML += givePageHTML(page) 
    return HttpResponse("Loading site id '%s', name was '%s'<br/>%s" %(s.pk ,s.name,pageHTML))


def page(request, page_id):
    try:
        p = Page.objects.get(pk=page_id)
    except Page.DoesNotExist:                
        raise Http404            
    return HttpResponse(givePageHTML(p))

def givePageHTML(page):
    return "<h1>%s</h1> <p>%s</p>" %(page.title ,page.html)