from django.contrib import admin
from .models import ImageFile, Image


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
    """
    Filter for ImageFileAdmin that allows filtering on mhd or raw/zraw files
    """

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


admin.site.register(Image, ImageAdmin)
admin.site.register(ImageFile, ImageFileAdmin)
