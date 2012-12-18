import pdb
from os import path

from django.core.files import File

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect,HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic.simple import direct_to_template


from filetransfers.forms import UploadForm
# FIXME : Sjoerd: comicmodels and filetransfers are being merged here. How to keep original Filetransfers seperate from this?
# Right now I feel as though I am entangeling things.. come back to this later  
from comicmodels.models import UploadModel
from filetransfers.api import prepare_upload, serve_file

from comicmodels.models import FileSystemDataset 

def upload_handler(request):
    view_url = reverse('filetransfers.views.upload_handler')
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
        return HttpResponseRedirect(view_url)

    upload_url, upload_data = prepare_upload(request, view_url)
    form = UploadForm()
            
    return direct_to_template(request, 'upload/upload.html',
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
    
    
def download_handler_filename(request, project_name, dataset_title,filename):    
    """offer file for download based on filename """
    
    dataset = FileSystemDataset.objects.get(comicsite__short_name=project_name,title=dataset_title)        
    filefolder = dataset.get_full_folder_path()
    filepath = path.join(filefolder,filename)
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


    