from urllib.parse import urlencode

from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from grandchallenge.components.admin import ComponentImageAdmin
from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstations.models import (
    Feedback,
    Session,
    Workstation,
    WorkstationImage,
)


class SessionHistoryAdmin(SimpleHistoryAdmin):
    ordering = ("-created",)
    list_display = [
        "pk",
        "created",
        "maximum_duration",
        "status",
        "creator",
        "region",
        "ping_times",
    ]
    list_filter = ["status", "region", "workstation_image__workstation__slug"]
    readonly_fields = [
        "creator",
        "workstation_image",
        "status",
        "logs",
        "region",
        "ping_times",
        "auth_token",
    ]
    search_fields = [
        "logs",
        "creator__username",
    ]


class FeedbackAdmin(ModelAdmin):
    readonly_fields = (
        "user_comment",
        "session",
        "screenshot",
        "context",
        "github_link",
    )
    list_display = ("session", "github_link")
    search_fields = [
        "session__pk",
        "session__creator__username",
        "user_comment",
    ]
    list_select_related = ("session__creator",)

    class Meta:
        model = Feedback

    @admin.display(description="Github link")
    def github_link(self, obj):
        params = {
            "labels": "bug",
            "title": "Bug report for session: " + str(obj.session.pk),
            "body": "Admin link: "
            + reverse(
                "admin:workstations_feedback_change",
                kwargs={"object_id": obj.pk},
            )
            + "\n\n"
            + obj.user_comment,
        }
        return format_html(
            '<a href="{}">{}</a>',
            "https://github.com/diagnijmegen/rse-cirrus-core/issues/new?"
            + urlencode(params),
            "Create issue",
        )


admin.site.register(Workstation)
admin.site.register(WorkstationImage, ComponentImageAdmin)
admin.site.register(Session, SessionHistoryAdmin)
admin.site.register(Feedback, FeedbackAdmin)
