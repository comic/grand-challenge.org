from django.contrib import admin
from .models import Study
from grandchallenge.retina_images.admin import ImageInline


class StudyInline(admin.StackedInline):
    model = Study
    extra = 0


class StudyAdmin(admin.ModelAdmin):
    search_fields = (
        "patient__identifier",
        "identifier",
        "referring_physicians_name",
        "accession_number",
    )
    list_filter = ("datetime",)
    inlines = [ImageInline]


admin.site.register(Study, StudyAdmin)
