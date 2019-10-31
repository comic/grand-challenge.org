from django.contrib import admin

from grandchallenge.archives.models import Archive


class ArchiveAdmin(admin.ModelAdmin):
    fieldsets = []
    inlines = []
    search_fields = ("name",)


admin.site.register(Archive, ArchiveAdmin)
