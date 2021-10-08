from django.contrib import admin

from grandchallenge.studies.models import Study


class StudyInline(admin.StackedInline):
    model = Study
    extra = 0


class StudyAdmin(admin.ModelAdmin):
    search_fields = ("patient__name", "name")
    list_filter = ("datetime",)


admin.site.register(Study, StudyAdmin)
