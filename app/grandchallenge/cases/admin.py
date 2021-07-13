import re
from functools import update_wrapper

from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.urls import path
from django.utils.html import format_html
from guardian.admin import GuardedModelAdmin

from grandchallenge.cases.models import (
    Image,
    ImageFile,
    RawImageFile,
    RawImageUploadSession,
)
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile
from grandchallenge.subdomains.utils import reverse


class ImageFileInline(admin.StackedInline):
    model = ImageFile
    extra = 0


class ImageAdmin(GuardedModelAdmin):
    search_fields = (
        "pk",
        "name",
        "study__name",
        "modality__modality",
        "color_space",
        "eye_choice",
        "field_of_view",
        "stereoscopic_choice",
        "study__patient__name",
    )
    list_filter = (
        "modality",
        "color_space",
        "eye_choice",
        "field_of_view",
        "stereoscopic_choice",
    )
    inlines = [ImageFileInline]
    readonly_fields = ("origin",)


class ImageInline(admin.StackedInline):
    model = Image
    extra = 0


class MhdOrRawFilter(admin.SimpleListFilter):
    """Allow filtering on mhd or raw/zraw files."""

    title = "MHD or RAW file"
    parameter_name = "mhd_or_raw"

    def lookups(self, request, model_admin):
        return (("mhd", "MHD file"), ("raw", "RAW/ZRAW file"))

    def queryset(self, request, queryset):
        if self.value() == "mhd":
            return queryset.filter(file__endswith=".mhd")
        if self.value() == "raw":
            return queryset.filter(file__endswith="raw")


class ImageFileAdmin(GuardedModelAdmin):
    search_fields = ("pk", "file", "image__name")
    list_filter = (MhdOrRawFilter,)
    readonly_fields = ("image",)


class RawImageUploadSessionAdmin(GuardedModelAdmin):
    ordering = ("-created",)
    list_display = (
        "pk",
        "created",
        "creator",
        "status",
        "error_message",
    )
    readonly_fields = (
        "creator",
        "status",
    )
    list_filter = ("status",)
    search_fields = (
        "creator__username",
        "pk",
        "error_message",
    )


class DownloadableFilter(admin.SimpleListFilter):
    """Allow filtering on downloadable files."""

    title = "Downloadable"
    parameter_name = "downloadable"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"),)

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(staged_file_id__isnull=False)
        return queryset


class RawImageFileAdmin(GuardedModelAdmin):
    list_filter = (DownloadableFilter,)
    list_display = ("filename", "upload_session", "download")
    readonly_fields = (
        "download",
        "upload_session",
    )
    search_fields = ("upload_session__pk", "filename")

    def download(self, instance):
        if not instance.staged_file_id:
            return
        return format_html(
            f'<a class="button" href={reverse(f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_download", kwargs={"object_id": instance.pk})}>Download</a>'
        )

    def download_view(self, request, object_id, **kwargs):
        obj = self.get_object(request, unquote(object_id), None)
        if not self.has_view_or_change_permission(request, obj):
            raise PermissionDenied

        try:
            with StagedAjaxFile(obj.staged_file_id).open() as saf:
                response = HttpResponse(
                    saf.read(), content_type="application/dicom"
                )
            response[
                "Content-Disposition"
            ] = f'attachment; filename="{obj.filename}"'
            return response
        except Exception:
            raise Http404("File not found")

    def get_urls(self):
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)

            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        urls = super().get_urls()

        download_url = path(
            "<path:object_id>/download/",
            wrap(self.download_view),
            name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_download",
        )
        # Currently the last url in ModelAdmin's get-urls is this:
        # # For backwards compatibility (was the change url before 1.9)
        #   path('<path:object_id>/', wrap(RedirectView.as_view(
        #       pattern_name='%s:%s_%s_change' % ((self.admin_site.name,) + info)
        #   ))),
        # This would also match <path:object_id>/download/ and is only there for
        # old django versions, which we do not use. Replace it if it is there.
        # Otherwise just append the download_url to the list.
        if urls[-1].pattern.regex == re.compile("^(?P<object_id>.+)/$"):
            urls[-1] = download_url
        else:
            urls.append(download_url)

        return urls


admin.site.register(Image, ImageAdmin)
admin.site.register(ImageFile, ImageFileAdmin)
admin.site.register(RawImageUploadSession, RawImageUploadSessionAdmin)
admin.site.register(RawImageFile, RawImageFileAdmin)
