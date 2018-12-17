from django.contrib import admin
from .models import ImageFile, Image


class ImageFileInline(admin.StackedInline):
    model = ImageFile
    extra = 0


class ImageAdmin(admin.ModelAdmin):
    search_fields = (
        "pk",
        "name",
    )
    inlines = [ImageFileInline]


admin.site.register(Image, ImageAdmin)
admin.site.register(ImageFile)
