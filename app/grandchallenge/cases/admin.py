from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from grandchallenge.cases.models import (
    Image,
    ImageFile,
    RawImageFile,
    RawImageUploadSession,
)


class ImageFileInline(admin.StackedInline):
    model = ImageFile
    extra = 0


class ImageAdmin(GuardedModelAdmin):
    search_fields = (
        "pk",
        "name",
        "modality__modality",
        "color_space",
        "eye_choice",
        "field_of_view",
        "stereoscopic_choice",
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


class RawImageFileAdmin(GuardedModelAdmin):
    list_display = ("filename", "upload_session")
    readonly_fields = ("upload_session",)
    search_fields = ("upload_session__pk", "filename")


admin.site.register(Image, ImageAdmin)
admin.site.register(ImageFile, ImageFileAdmin)
admin.site.register(RawImageUploadSession, RawImageUploadSessionAdmin)
admin.site.register(RawImageFile, RawImageFileAdmin)
