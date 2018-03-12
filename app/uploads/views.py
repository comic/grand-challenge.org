import ntpath
import os
import posixpath
from urllib.parse import unquote

from ckeditor_uploader.views import browse
from django.conf import settings
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.core.files import File
from django.core.files.storage import DefaultStorage
from django.core.urlresolvers import reverse
from django.http import (
    HttpResponseRedirect,
    Http404,
    HttpResponseForbidden,
)
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView

from comicmodels.models import UploadModel, ComicSite, Page
from comicmodels.permissions import can_access
from comicsite.permissions.mixins import UserIsChallengeAdminMixin
from comicsite.views import getSite, site_get_standard_vars, permissionMessage
from pages.views import ComicSiteFilteredQuerysetMixin
from uploads.api import serve_file
from uploads.emails import send_file_uploaded_notification_email
from uploads.forms import UserUploadForm, CKUploadForm


class UploadList(UserIsChallengeAdminMixin, ComicSiteFilteredQuerysetMixin,
                 ListView):
    model = UploadModel


# TODO: adapt this for ckeditor
class CKUploadView(UserIsChallengeAdminMixin, CreateView):
    model = UploadModel
    form_class = CKUploadForm

    # TODO: remove, unneeded once moved to ckeditor
    def get_success_url(self):
        return reverse('uploads:list', args=[self.request.projectname])

    @method_decorator(csrf_exempt)  # Required by django-ckeditor
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.comicsite = ComicSite.objects.get(
            pk=self.request.project_pk)
        form.instance.user = self.request.user
        form.instance.file = form.cleaned_data['upload']

        return super().form_valid(form)


# TODO: permissions, limit by folder
def ck_browse_uploads(request, challenge_short_name):
    return browse(request)


def serve(request, project_name, path, document_root=None):
    """
    Serve static file for a given project.

    This is meant as a replacement for the inefficient debug only
    'django.views.static.serve' way of serving files under /media urls.

    """

    if document_root is None:
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
    fullpath = os.path.join(document_root, project_name, newpath)

    storage = DefaultStorage()

    if not storage.exists(fullpath):

        # On case sensitive filesystems you can have problems if the project
        # nameurl in the url is not exactly the same case as the filepath.
        # find the correct case for projectname then.

        projectlist = ComicSite.objects.filter(short_name=project_name)
        if not projectlist:
            raise Http404("project '%s' does not exist" % project_name)

        project_name = projectlist[0].short_name
        fullpath = os.path.join(document_root, project_name, newpath)

    if not storage.exists(fullpath):
        raise Http404('"%(path)s" does not exist' % {'path': fullpath})

    if can_access(request.user, path, project_name):
        try:
            f = storage.open(fullpath, 'rb')
            file = File(f)  # create django file object
        except IOError:
            return HttpResponseForbidden("This is not a file")

        # Do not offer to save images, but show them directly
        return serve_file(file, save_as=True)
    else:
        return HttpResponseForbidden("This file is not available without "
                                     "credentials")


def upload_handler(request, challenge_short_name):
    """
    Upload a file to the given comicsite, display files previously uploaded
    """

    view_url = reverse(
        'uploads:create',
        kwargs={'challenge_short_name': challenge_short_name}
    )

    if request.method == 'POST':
        # set values excluded from form here to make the model validate
        site = getSite(challenge_short_name)
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

            send_file_uploaded_notification_email(
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

    [site, pages, metafooterpages] = site_get_standard_vars(
        challenge_short_name)

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
        'uploads/comicupload.html',
        {
            'form': form,
            'upload_url': view_url,
            'site': site,
            'pages': pages,
            'metafooterpages': metafooterpages
        },
    )
