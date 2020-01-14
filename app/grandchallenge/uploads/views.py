from os.path import basename

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import ListView

from grandchallenge.core.permissions.mixins import UserIsChallengeAdminMixin
from grandchallenge.pages.models import ErrorPage, Page
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
    """Upload a file to the given challenge, display files previously uploaded."""
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
            "pages/page_detail.html",
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
        "uploads/uploadmodel_detail.html",
        {
            "form": form,
            "upload_url": view_url,
            "challenge": challenge,
            "pages": pages,
        },
    )


def permission_message(request, p):
    if request.user.is_authenticated:
        msg = """
        <div class="system_message">
            <h2>Restricted page</h2>
            <p>
                This page can only be viewed by participants of this
                project to view this page please make sure of the following:
            </p>
            <ul>
                <li>
                    First, log in to this site by using the 'Sign in'
                    button at the top right.
                </li>
                <li>
                    Second, you need to join / register with the
                    specific project you are interested in as a
                    participant. The link to do this is provided by the
                    project organizers on the project website.
                </li>
            </ul>
        <div>
        """
        title = p.title
    else:
        msg = (
            "The page '"
            + p.title
            + "' can only be viewed by registered users. Please sign in to view this page."
        )
        title = p.title

    return ErrorPage(challenge=request.challenge, title=title, html=msg)
