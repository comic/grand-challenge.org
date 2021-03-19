from django.contrib import admin

from grandchallenge.publications.forms import PublicationForm
from grandchallenge.publications.models import Publication


class PublicationAdmin(admin.ModelAdmin):
    list_display = [
        "identifier",
        "year",
        "title",
        "referenced_by_count",
        "citation",
    ]
    readonly_fields = [
        "title",
        "referenced_by_count",
        "csl",
        "ama_html",
        "year",
        "citation",
    ]
    form = PublicationForm
    search_fields = (
        "title",
        "year",
        "identifier",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ["identifier"]
        else:
            return self.readonly_fields


admin.site.register(Publication, PublicationAdmin)
