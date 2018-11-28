from django.contrib import admin
from .models import Archive


class ArchiveAdmin(admin.ModelAdmin):
    fieldsets = []
    inlines = []
    search_fields = ("name",)


admin.site.register(Archive, ArchiveAdmin)
