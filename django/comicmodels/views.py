# Create your views here.

from os import path

#from django.core.files import File
#
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
#from django.shortcuts import get_object_or_404
from django.views.generic.simple import direct_to_template
#
from comicmodels.forms import UploadForm
from comicmodels.models import UploadModel
from filetransfers.api import prepare_upload, serve_file
#
#from comicmodels.models import FileSystemDataset


def upload_handler(request,site_short_name):
    view_url = reverse('comicmodels.views.upload_handler',kwargs={'site_short_name':site_short_name})
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
