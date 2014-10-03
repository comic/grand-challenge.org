import pdb
import posixpath
import re
import os
try:
    from urllib.parse import unquote
except ImportError:     # Python 2
    from urllib import unquote
from exceptions import Exception

from django.core.files import File
from django.core.files.storage import DefaultStorage
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.http import Http404
from django.utils.translation import ugettext as _, ugettext_noop
#from django.views.generic.simple import direct_to_template

from filetransfers.forms import UploadForm
# FIXME : Sjoerd: comicmodels and filetransfers are being merged here. How to keep original Filetransfers seperate from this?
# Right now I feel as though I am entangeling things.. come back to this later
from filetransfers.api import prepare_upload, serve_file
from comicmodels.models import FileSystemDataset,ComicSite,UploadModel,ComicSiteModel
from django.conf import settings

def upload_handler(request):
    view_url = reverse('filetransfers.views.upload_handler')
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
        return HttpResponseRedirect(view_url)

    upload_url, upload_data = prepare_upload(request, view_url)
    form = UploadForm()

    #return direct_to_template(request, 'upload/upload.html',
    return render(request, 'upload/upload.html',
        {'form': form, 'upload_url': upload_url, 'upload_data': upload_data,
         'uploads': UploadModel.objects.all()})

def download_handler(request, pk):
    upload = get_object_or_404(UploadModel, pk=pk)
    return serve_file(request, upload.file, save_as=True)


def uploadedfileserve_handler(request, pk):
    """ Serve a file through django, for displaying images etc. """
    upload = get_object_or_404(UploadModel, pk=pk)

    #if request.user.has_perm("comicmodels.view_ComicSiteModel"):
    if upload.can_be_viewed_by(request.user):
        return serve_file(request, upload.file, save_as=False)
    else:
        return HttpResponse("You do not have permission to view this.")


def download_handler_dataset_file(request, project_name, dataset_title,filename):
    """offer file for download based on filename and dataset"""

    dataset = FileSystemDataset.objects.get(comicsite__short_name=project_name,title=dataset_title)
    filefolder = dataset.get_full_folder_path()
    filepath = os.path.join(filefolder,filename)
    f = open(filepath, 'r')
    file = File(f) # create django file object

    return serve_file(request, file, save_as=True)

def download_handler_file(request, filepath):
    """offer file for download based on filepath relative to django root"""

    f = open(filepath, 'r')
    file = File(f) # create django file object

    return serve_file(request, file, save_as=True)


def delete_handler(request, pk):
    if request.method == 'POST':
        upload = get_object_or_404(UploadModel, pk=pk)
        comicsitename = upload.comicsite.short_name
        try:
            upload.file.delete()  #if no file object can be found just continue
        except:
            pass
        finally:
            pass
            upload.delete()

    return HttpResponseRedirect(reverse('comicmodels.views.upload_handler',kwargs={'site_short_name':comicsitename}))


def can_access(user,path,project_name,override_permission=""):
    """ Does this user have permission to access folder path which is part of
    project named project_name?
    Override permission can be used to make certain folders servable through
    code even though this would not be allowed otherwise
         
    """
    if override_permission == "":
        required = _required_permission(user,path,project_name)
    else:
        choices = [x[0] for x in ComicSiteModel.PERMISSIONS_CHOICES]
        if not override_permission in choices:
            raise Exeption("input parameters should be one of [%s], "
                           "found '%s' " % (",".join(choices),needed))
        required = override_permission
    
    if required == ComicSiteModel.ALL:
        return True
    elif required == ComicSiteModel.REGISTERED_ONLY:
        project = ComicSite.objects.get(short_name=project_name)        
        if project.is_participant(user):
            return True
        else:
            return False
    elif required == ComicSiteModel.ADMIN_ONLY:
        project = ComicSite.objects.get(short_name=project_name)
        if project.is_admin(user):
            return True
        else:
            return False
    else:
        return False


def _sufficient_permission(needed,granted):
    """ Return true if granted permission is greater than or equal to needed
    permission. 
    
    """
    choices = [x[0] for x in CoomicSiteModel.PERMISSIONS_CHOICES]        
    
    if not needed in choices:
        raise Exeption("input parameters should be one of [%s], found '%s' " % (",".join(choices),needed))
    if not granted in choices:
        raise Exeption("input parameters should be one of [%s], found '%s' " % (",".join(choices),granted))
    
    if ComicSiteModel.PERMISSION_WEIGHTS[needed] >= ComicSiteModel.PERMISSION_WEIGHTS[granted]:
        return True
    else:
        return False


def _required_permission(user,path,project_name):
    """ Given a file path on local filesystem, which permission level is needed
    to view this?
     
    """
    #some config checking. 
    # TODO : check this once at server start but not every time this method is
    # called. It is too late to throw this error once a user clicks 
    # something.
    if not hasattr(settings,"COMIC_PUBLIC_FOLDER_NAME"):
        raise ImproperlyConfigured("Don't know from which folder serving publiv files"
                                   "is allowed. Please add a setting like "
                                   "'COMIC_PUBLIC_FOLDER_NAME = \"public_html\""
                                   " to your .conf file." )
    
    if not hasattr(settings,"COMIC_REGISTERED_ONLY_FOLDER_NAME"):
        raise ImproperlyConfigured("Don't know from which folder serving protected files"
                                   "is allowed. Please add a setting like "
                                   "'COMIC_REGISTERED_ONLY_FOLDER_NAME = \"datasets\""
                                   " to your .conf file." )
    
    if hasattr(settings,"COMIC_ADDITIONAL_PUBLIC_FOLDER_NAMES"):
        if startwith_any(path,settings.COMIC_ADDITIONAL_PUBLIC_FOLDER_NAMES):
            return ComicSiteModel.ALL
        
    if path.startswith(settings.COMIC_PUBLIC_FOLDER_NAME):
        return ComicSiteModel.ALL            
    elif path.startswith(settings.COMIC_REGISTERED_ONLY_FOLDER_NAME):
        return ComicSiteModel.REGISTERED_ONLY
    else:
        return ComicSiteModel.ADMIN_ONLY
 
def startwith_any(path,start_options):
    """ Return true if path starts with any of the strings in string array start_options
     
    """    
    for option in start_options:
        if path.startswith(option):
            return True
    
    return False

def serve(request, project_name, path, document_root=None,override_permission=""):
    """
    Serve static file for a given project. 
    
    This is meant as a replacement for the inefficient debug only 
    'django.views.static.serve' way of serving files under /media urls.
     
    """        
    
    if document_root == None:
        document_root = settings.MEDIA_ROOT
    
    path = posixpath.normpath(unquote(path))
    path = path.lstrip('/')
    newpath = ''
    for part in path.split('/'):
        if not part:
            # Strip empty path components.
            continue
        drive, part = os.path.splitdrive(part)
        head, part = os.path.split(part)
        if part in (os.curdir, os.pardir):
            # Strip '.' and '..' in path.
            continue
        newpath = os.path.join(newpath, part).replace('\\', '/')
    if newpath and path != newpath:
        return HttpResponseRedirect(newpath)    
    fullpath = os.path.join(document_root,project_name, newpath)
    
    
    storage = DefaultStorage()
    if not storage.exists(fullpath):
        
        # On case sensitive filesystems you can have problems if the project 
        # nameurl in the url is not exactly the same case as the filepath. 
        # find the correct case for projectname then.
        # Also case sensitive file systems are weird.
        # who would ever want to have a folder 'data' and 'Data' contain 
        # different files?            
        
        projectlist = ComicSite.objects.filter(short_name=project_name)
        if projectlist == []:
            raise Http404(_("project '%s' does not exist" % project_name ))
    
        project_name = projectlist[0].short_name 
        fullpath = os.path.join(document_root,project_name, newpath)
    
    if not storage.exists(fullpath):
        raise Http404(_('"%(path)s" does not exist') % {'path': fullpath})
    
    
    if can_access(request.user,path,project_name,override_permission):    
        f = storage.open(fullpath, 'rb')
        file = File(f) # create django file object
        # Do not offer to save images, but show them directly
        return serve_file(request, file, save_as=True)
    else:        
        return HttpResponseForbidden("This file is not available without "
                                    "credentials")        
        
    
        
       
        
    
    

    



