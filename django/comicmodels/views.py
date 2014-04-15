# Create your views here.
import pdb
from os import path
import ntpath

from django.contrib import messages
from django.contrib.sites.models import get_current_site
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, render

from comicmodels.models import ComicSite
from comicmodels.forms import UploadForm,UserUploadForm
from comicmodels.models import UploadModel,Page
from comicmodels.signals import file_uploaded
from comicsite.template.context import CurrentAppRequestContext
from comicsite.views import site_get_standard_vars,concatdicts,getSite,permissionMessage

from filetransfers.api import prepare_upload, serve_file


def upload_handler(request,site_short_name):
    """ Upload a file to the given comicsite, display files previously uploaded"""

    view_url = reverse('comicmodels.views.upload_handler',kwargs={'site_short_name':site_short_name})

    if request.method == 'POST':
        # set values excluded from form here to make the model validate
        site = getSite(site_short_name)
        uploadedFile = UploadModel(comicsite=site,permission_lvl = UploadModel.ADMIN_ONLY,user=request.user)
        #ADMIN_ONLY
                
        form = UserUploadForm(request.POST, request.FILES, instance=uploadedFile)        
        if form.is_valid():
            form.save()
            filename = ntpath.basename(form.instance.file.file.name)
            messages.success(request, "File '%s' sucessfully uploaded. An email has been sent to this\
                                       projects organizers." % filename)
            
            # send signal to be picked up by email notifier 03/2013 - Sjoerd. I'm not sure that sending
            # signals is the best way to do this. Why not just call the method directly?
            # typical case for a refactoring round.                 
            file_uploaded.send(sender=UploadModel,uploader=request.user,filename=filename,comicsite=site
                                   ,site=get_current_site(request))
            

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

        response = render_to_response('page.html',
                                       {'site': site,
                                        'currentpage': currentpage, 
                                        "pages":pages,                                            
                                        "metafooterpages":metafooterpages},
                                       context_instance=CurrentAppRequestContext(request))
        
        response.status_code = 403
        return response



    if request.user.is_superuser or site.is_admin(request.user):
        uploadsforcurrentsite = UploadModel.objects.filter(comicsite=site).\
                                order_by('modified').reverse()
    else:
        uploadsforcurrentsite = UploadModel.objects.filter(user=request.user,comicsite=site).\
                                order_by('modified').reverse()

    #return direct_to_template(request, 'upload/comicupload.html',
    return render_to_response('upload/comicupload.html',
        {'form': form, 'upload_url': upload_url, 'upload_data': upload_data,
         'uploads': uploadsforcurrentsite,'site': site,'pages': pages,
         'metafooterpages' : metafooterpages},
          context_instance=CurrentAppRequestContext(request))


