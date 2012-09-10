import pdb

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic.simple import direct_to_template

from filetransfers.forms import UploadForm
from filetransfers.models import UploadModel

from filetransfers.api import prepare_upload, serve_file

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

def delete_handler(request, pk):
    if request.method == 'POST':
        upload = get_object_or_404(UploadModel, pk=pk)
        upload.file.delete()
        upload.delete()
    return HttpResponseRedirect(reverse('filetransfers.views.upload_handler'))


    