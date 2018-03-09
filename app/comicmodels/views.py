# Create your views here.
import ntpath

from auth_mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import CreateView

from comicmodels.forms import UserUploadForm, ChallengeForm
from comicmodels.models import UploadModel, Page, ComicSite
from comicmodels.signals import file_uploaded
from comicsite.views import site_get_standard_vars, getSite, permissionMessage


def upload_handler(request, site_short_name):
    """
    Upload a file to the given comicsite, display files previously uploaded
    """

    view_url = reverse('challenge-upload-handler',
                       kwargs={'site_short_name': site_short_name})

    if request.method == 'POST':
        # set values excluded from form here to make the model validate
        site = getSite(site_short_name)
        uploadedFile = UploadModel(comicsite=site,
                                   permission_lvl=UploadModel.ADMIN_ONLY,
                                   user=request.user)
        # ADMIN_ONLY

        form = UserUploadForm(request.POST, request.FILES,
                              instance=uploadedFile)
        if form.is_valid():
            form.save()
            filename = ntpath.basename(form.instance.file.file.name)
            messages.success(
                request,
                (
                    f"File '{filename}' sucessfully uploaded. "
                    f"An email has been sent to this projects organizers."
                )
            )

            # send signal to be picked up by email notifier 03/2013 - Sjoerd.
            # I'm not sure that sending signals is the best way to do this.
            # Why not just call the method directly?
            # typical case for a refactoring round.
            file_uploaded.send(
                sender=UploadModel,
                uploader=request.user,
                filename=filename,
                comicsite=site,
                site=get_current_site(request),
            )

            return HttpResponseRedirect(view_url)
        else:
            # continue to showing errors
            pass
    else:
        form = UserUploadForm()

    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)

    if not (site.is_admin(request.user) or site.is_participant(request.user)):
        p = Page(comicsite=site, title="files")
        currentpage = permissionMessage(request, site, p)

        response = render(
            request,
            'page.html',
            {
                'site': site,
                'currentpage': currentpage,
                "pages": pages,
                "metafooterpages": metafooterpages
            },
        )

        response.status_code = 403
        return response

    return render(
        request,
        'upload/comicupload.html',
        {
            'form': form,
            'upload_url': view_url,
            'site': site,
            'pages': pages,
            'metafooterpages': metafooterpages
        },
    )


class ChallengeCreate(LoginRequiredMixin, CreateView):
    model = ComicSite
    form_class = ChallengeForm

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super(ChallengeCreate, self).form_valid(form)
