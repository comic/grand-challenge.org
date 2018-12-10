from django.contrib import admin
from .models import Study
from grandchallenge.retina_images.admin import ImageInline


class StudyInline(admin.StackedInline):
    model = Study
    extra = 0


class StudyAdmin(admin.ModelAdmin):
    search_fields = (
        "patient__name",
        "name",
    )
    list_filter = ("datetime",)
    inlines = [ImageInline]


admin.site.register(Study, StudyAdmin)
