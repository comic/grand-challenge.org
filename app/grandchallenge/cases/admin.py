from django.contrib import admin

from grandchallenge.cases.models import (
    Image,
    ImageFile,
    ImageGroupObjectPermission,
    ImageUserObjectPermission,
    PostProcessImageTask,
    RawImageUploadSession,
    RawImageUploadSessionGroupObjectPermission,
    RawImageUploadSessionUserObjectPermission,
)
from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)


class ImageFileInline(admin.StackedInline):
    model = ImageFile
    extra = 0


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
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


@admin.register(ImageFile)
class ImageFileAdmin(admin.ModelAdmin):
    search_fields = ("pk", "file", "image__name")
    list_filter = (MhdOrRawFilter,)
    readonly_fields = ("image",)


@admin.register(RawImageUploadSession)
class RawImageUploadSessionAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = ("pk", "created", "creator", "status", "error_message")
    readonly_fields = ("creator", "status")
    list_filter = ("status",)
    search_fields = ("creator__username", "pk", "error_message")


@admin.register(PostProcessImageTask)
class PostProcessImageTaskAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = ("pk", "created", "image", "status")
    readonly_fields = ("image",)
    list_filter = ("status",)
    search_fields = ("pk", "image__pk")


admin.site.register(ImageUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(ImageGroupObjectPermission, GroupObjectPermissionAdmin)
admin.site.register(
    RawImageUploadSessionUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    RawImageUploadSessionGroupObjectPermission, GroupObjectPermissionAdmin
)
