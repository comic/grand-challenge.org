from os.path import basename

from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import ListView

from grandchallenge.core.permissions.mixins import UserIsChallengeAdminMixin
from grandchallenge.core.views import permissionMessage
from grandchallenge.pages.models import Page
from grandchallenge.pages.views import ChallengeFilteredQuerysetMixin
from grandchallenge.subdomains.utils import reverse
from grandchallenge.uploads.emails import send_file_uploaded_notification_email
from grandchallenge.uploads.forms import UserUploadForm
from grandchallenge.uploads.models import UploadModel


class UploadList(
    UserIsChallengeAdminMixin, ChallengeFilteredQuerysetMixin, ListView
):
    model = UploadModel


def upload_handler(request):
    """
    Upload a file to the given comicsite, display files previously uploaded
    """
    site = request.challenge

    view_url = reverse(
        "uploads:create", kwargs={"challenge_short_name": site.short_name}
    )

    if request.method == "POST":
        # set values excluded from form here to make the model validate
        uploadedFile = UploadModel(
            challenge=site,
            permission_lvl=UploadModel.ADMIN_ONLY,
            user=request.user,
        )
        # ADMIN_ONLY
        form = UserUploadForm(
            request.POST, request.FILES, instance=uploadedFile
        )
        if form.is_valid():
            form.save()
            filename = basename(form.instance.file.file.name)
            messages.success(
                request,
                (
                    f"File '{filename}' sucessfully uploaded. "
                    f"An email has been sent to this projects organizers."
                ),
            )
            send_file_uploaded_notification_email(
                uploader=request.user,
                filename=filename,
                challenge=site,
                site=get_current_site(request),
            )
            return HttpResponseRedirect(view_url)

        else:
            # continue to showing errors
            pass
    else:
        form = UserUploadForm()

    pages = site.page_set.all()

    if not (site.is_admin(request.user) or site.is_participant(request.user)):
        p = Page(challenge=site, title="files")
        currentpage = permissionMessage(request, p)
        response = render(
            request,
            "page.html",
            {"site": site, "currentpage": currentpage, "pages": pages},
        )
        response.status_code = 403
        return response

    return render(
        request,
        "uploads/comicupload.html",
        {"form": form, "upload_url": view_url, "site": site, "pages": pages},
    )
