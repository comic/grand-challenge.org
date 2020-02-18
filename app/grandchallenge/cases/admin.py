from django.contrib import admin
from django.utils.safestring import mark_safe

from grandchallenge.cases.models import (
    Image,
    ImageFile,
    RawImageFile,
    RawImageUploadSession,
)
from grandchallenge.subdomains.utils import reverse


class ImageFileInline(admin.StackedInline):
    model = ImageFile
    extra = 0


class ImageAdmin(admin.ModelAdmin):
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


class ImageFileAdmin(admin.ModelAdmin):
    search_fields = ("pk", "file", "image")
    list_filter = (MhdOrRawFilter,)


class RawImageUploadSessionAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = (
        "pk",
        "created",
        "creator",
        "status",
        "error_message",
        "algorithm",
        "reader_study",
    )
    readonly_fields = (
        "creator",
        "algorithm_image",
        "imageset",
        "annotationset",
        "algorithm_result",
        "reader_study",
        "status",
    )
    list_select_related = (
        "algorithm_image__algorithm",
        "algorithm_result__job__algorithm_image__algorithm",
    )
    list_filter = ("status",)
    search_fields = (
        "creator__username",
        "algorithm_image__algorithm__title",
        "algorithm_result__job__algorithm_image__algorithm__title",
        "reader_study__title",
        "pk",
        "error_message",
    )

    def algorithm(self, obj):
        if obj.algorithm_image:
            return obj.algorithm_image.algorithm
        elif obj.algorithm_result:
            return obj.algorithm_result.job.algorithm_image.algorithm


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


class RawImageFileAdmin(admin.ModelAdmin):
    list_filter = (DownloadableFilter,)
    list_display = ("filename", "upload_session", "download")
    readonly_fields = ("download",)

    def download(self, instance):
        if not instance.staged_file_id:
            return
        return mark_safe(
            f'<a class="button" href={reverse("api:upload-session-file-download", kwargs={"pk": instance.pk})}>Download</a>'
        )


admin.site.register(Image, ImageAdmin)
admin.site.register(ImageFile, ImageFileAdmin)
admin.site.register(RawImageUploadSession, RawImageUploadSessionAdmin)
admin.site.register(RawImageFile, RawImageFileAdmin)
