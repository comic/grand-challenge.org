# Create your views here.
import pdb
from os import path

#from django.core.files import File
#
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
#from django.shortcuts import get_object_or_404
from django.views.generic.simple import direct_to_template
#
from comicmodels.models import ComicSite
from comicmodels.forms import UploadForm,UserUploadForm
from comicmodels.models import UploadModel
from comicsite.views import site_get_standard_vars,concatdicts,getSite
from filetransfers.api import prepare_upload, serve_file
#
#from comicmodels.models import FileSystemDataset


def upload_handler(request,site_short_name):
    """ Upload a file to the given comicsite, display files previously uploaded"""
    
    view_url = reverse('comicmodels.views.upload_handler',kwargs={'site_short_name':site_short_name})
    
    if request.method == 'POST':
        # set values excluded from form here to make the model validate
        site = getSite(site_short_name)
        uploadedFile = UploadModel(comicsite=site,permission_lvl = UploadModel.ALL,
                                   user=request.user)
        
        
        form = UserUploadForm(request.POST, request.FILES, instance=uploadedFile)
               
        if form.is_valid():        
            form.save()
            return HttpResponseRedirect(view_url)
        else:
            #continue to showing errors
            pass 
    else:
        form = UserUploadForm()

    upload_url, upload_data = prepare_upload(request, view_url)
    
    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)
    
    uploadsforcurrentsite = UploadModel.objects.filter(comicsite=site)
                
    
        
    
    return direct_to_template(request, 'upload/comicupload.html',
        {'form': form, 'upload_url': upload_url, 'upload_data': upload_data,
         'uploads': uploadsforcurrentsite,'site': site,'pages': pages, 
         'metafooterpages' : metafooterpages})

