from os.path import basename

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import ListView

from grandchallenge.core.permissions.mixins import UserIsChallengeAdminMixin
from grandchallenge.core.views import permission_message
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
    Upload a file to the given challenge, display files previously uploaded
    """
    challenge = request.challenge

    view_url = reverse(
        "uploads:create", kwargs={"challenge_short_name": challenge.short_name}
    )

    if request.method == "POST":
        # set values excluded from form here to make the model validate
        uploaded_file = UploadModel(
            challenge=challenge,
            permission_lvl=UploadModel.ADMIN_ONLY,
            user=request.user,
        )
        # ADMIN_ONLY
        form = UserUploadForm(
            request.POST, request.FILES, instance=uploaded_file
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
                challenge=challenge,
                site=request.site,
            )
            return HttpResponseRedirect(view_url)

        else:
            # continue to showing errors
            pass
    else:
        form = UserUploadForm()

    pages = challenge.page_set.all()

    if not (
        challenge.is_admin(request.user)
        or challenge.is_participant(request.user)
    ):
        p = Page(challenge=challenge, title="files")
        currentpage = permission_message(request, p)
        response = render(
            request,
            "page.html",
            {
                "challenge": challenge,
                "currentpage": currentpage,
                "pages": pages,
            },
        )
        response.status_code = 403
        return response

    return render(
        request,
        "uploads/comicupload.html",
        {
            "form": form,
            "upload_url": view_url,
            "challenge": challenge,
            "pages": pages,
        },
    )
