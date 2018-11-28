from django.contrib import admin
from .models import RetinaImage
from grandchallenge.annotations.admin import SingleLandmarkAnnotationInline


class ImageInline(admin.StackedInline):
    model = RetinaImage
    extra = 0


class ImageAdmin(admin.ModelAdmin):
    search_fields = (
        "name",
        "study__name",
        "study__patient__name",
        "archive_set__name",
        "modality",
    )
    list_filter = ("modality",)
    inlines = [SingleLandmarkAnnotationInline]


admin.site.register(RetinaImage, ImageAdmin)
