from django.contrib import admin

from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.utilization.models import SessionCost


@admin.register(SessionCost)
class SessionCostAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = (
        "pk",
        "created",
        "session",
        "creator",
        "duration",
        "credits_consumed",
        "accessed_reader_studies",
    )
    search_fields = (
        "creator__username",
        "pk",
        "reader_studies__slug",
        "reader_studies__pk",
    )
    readonly_fields = ("reader_studies", "credits_consumed")

    def accessed_reader_studies(self, obj):
        return oxford_comma(obj.reader_studies.all())
