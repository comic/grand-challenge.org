
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse,Http404,HttpResponseRedirect
from django.shortcuts import render_to_response,redirect
from django.template import RequestContext,Context,Template,TemplateSyntaxError

from dropbox import client, rest, session

from comicmodels.models import DropboxFolder


def test(request):
    return  HttpResponse("ANYTHING TEST")


# these methods are used for asynchronous calls in other parts of the framework

def get_connection_status(request,dropbox_folder_id):
    """Check whether this dropboxfolder can be accessed
    """
    # get dropbox folder item from db
    df = _getDropboxFolder(dropbox_folder_id)
    (status,msg) = df.get_connection_status()
    
    # return response
    return HttpResponse(msg)


def reset_connection(request,dropbox_folder_id):
    """ Generate a new link to authorize access to given dropbox. Will invalidate the old connection
    """
    #get dropbox folder from db
    df = _getDropboxFolder(dropbox_folder_id)
    callback_host = _get_host_path(request)
    (request_token,msg) = df.reset_connection(callback_host)
    request.session['request_token'] = request_token 
    
    return HttpResponse(msg)
    
def finalize_connection(request,dropbox_folder_id):
    """ after authorizing, get access token and save for later use
    """    
    request_token = request.session['request_token']
    df = _getDropboxFolder(dropbox_folder_id)
    msg = df.finalize_connection(request_token)
    
    #return HttpResponse(msg)
    url = reverse("admin:comicmodels_dropboxfolder_change",args=[df.pk])
    return HttpResponseRedirect(url)

def _getDropboxFolder(id):
    """ get dropbox folder item from django database
    """
    try:
        dropbox_folder = DropboxFolder.objects.get(pk=id)
    except DropboxFolder.DoesNotExist:                
        raise Http404   
    return dropbox_folder 

def _get_full_path(request):
    full_path = ('http', ('', 's')[request.is_secure()], '://', request.META['HTTP_HOST'], request.path)
    return ''.join(full_path)

def _get_host_path(request):
    full_path = ('http', ('', 's')[request.is_secure()], '://', request.META['HTTP_HOST'])
    return ''.join(full_path)
