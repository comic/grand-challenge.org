import ntpath

from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, TemplateView

from grandchallenge.core.permissions.mixins import UserIsChallengeAdminMixin
from grandchallenge.core.views import getSite, permissionMessage
from grandchallenge.pages.models import Page
from grandchallenge.pages.views import ChallengeFilteredQuerysetMixin
from grandchallenge.uploads.emails import send_file_uploaded_notification_email
from grandchallenge.uploads.forms import UserUploadForm, CKUploadForm
from grandchallenge.uploads.models import UploadModel


class UploadList(
    UserIsChallengeAdminMixin, ChallengeFilteredQuerysetMixin, ListView
):
    model = UploadModel


class CKUploadView(UserIsChallengeAdminMixin, CreateView):
    model = UploadModel
    form_class = CKUploadForm

    def get_success_url(self):
        return reverse(
            "uploads:list",
            kwargs={"challenge_short_name": self.request.challenge.short_name},
        )

    @method_decorator(csrf_exempt)  # Required by django-ckeditor
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.challenge = self.request.challenge
        form.instance.user = self.request.user
        form.instance.file = form.cleaned_data["upload"]
        super().form_valid(form)
        # Taken from ckeditor_uploader.views.ImageUploadView
        # Note that this function is heavily tied to the response there,
        # so check when updating django-ckeditor.
        # TODO: Write a selenium test to check this.
        ck_func_num = self.request.GET.get("CKEditorFuncNum")
        if ck_func_num:
            ck_func_num = escape(ck_func_num)
        url = form.instance.file.url
        if ck_func_num:
            # Respond with Javascript sending ckeditor upload url.
            return HttpResponse(
                """
            <script type='text/javascript'>
                window.parent.CKEDITOR.tools.callFunction({}, '{}');
            </script>""".format(
                    ck_func_num, url
                )
            )

        else:
            retdata = {
                "url": url,
                "uploaded": "1",
                "fileName": form.instance.file.name,
            }
            return JsonResponse(retdata)


class CKBrowseView(UserIsChallengeAdminMixin, TemplateView):
    template_name = "ckeditor/browse.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        uploaded_files = UploadModel.objects.filter(
            challenge=self.request.challenge, permission_lvl=UploadModel.ALL
        )
        files = []
        for uf in uploaded_files:
            src = uf.file.url
            files.append(
                {
                    "thumb": src,
                    "src": src,
                    "is_image": False,
                    "visible_filename": uf.file.name,
                }
            )
        context.update({"show_dirs": False, "files": files})
        return context


def upload_handler(request, challenge_short_name):
    """
    Upload a file to the given comicsite, display files previously uploaded
    """
    view_url = reverse(
        "uploads:create", kwargs={"challenge_short_name": challenge_short_name}
    )

    site = getSite(challenge_short_name)

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
            filename = ntpath.basename(form.instance.file.file.name)
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
        currentpage = permissionMessage(request, site, p)
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
