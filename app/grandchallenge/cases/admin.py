from django.contrib import admin
from .models import ImageFile, Image


class ImageFileInline(admin.StackedInline):
    model = ImageFile
    extra = 0


class ImageAdmin(admin.ModelAdmin):
    search_fields = ("pk", "name", "study__name", "modality", "color_space", "eye_choice")
    list_filter = ("modality", "color_space", "eye_choice")
    inlines = [ImageFileInline]


class ImageInline(admin.StackedInline):
    model = Image
    extra = 0


admin.site.register(Image, ImageAdmin)
admin.site.register(ImageFile)
