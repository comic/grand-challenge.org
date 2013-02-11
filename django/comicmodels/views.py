# Create your views here.
import pdb
from os import path

#from django.core.files import File
#
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
#from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic.simple import direct_to_template
#
from comicmodels.models import ComicSite
from comicmodels.forms import UploadForm,UserUploadForm
from comicmodels.models import UploadModel,Page
from comicsite.views import site_get_standard_vars,concatdicts,getSite,permissionMessage
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
        
        pdb.set_trace()
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
    
    if not (site.is_admin(request.user) or site.is_participant(request.user)):        
        
        p = Page(comicsite=site,title="files")
        currentpage = permissionMessage(request,site,p)
        
        return render_to_response('page.html', {'site': site, 'currentpage': currentpage, "pages":pages, 
                                            "metafooterpages":metafooterpages},
                                            context_instance=RequestContext(request))
  
    
            
    if request.user.is_superuser or site.is_admin(request.user):
        uploadsforcurrentsite = UploadModel.objects.filter(comicsite=site).\
                                order_by('modified').reverse()
    else:
        uploadsforcurrentsite = UploadModel.objects.filter(user=request.user).\
                                order_by('modified').reverse()
    
    return direct_to_template(request, 'upload/comicupload.html',
        {'form': form, 'upload_url': upload_url, 'upload_data': upload_data,
         'uploads': uploadsforcurrentsite,'site': site,'pages': pages, 
         'metafooterpages' : metafooterpages})


