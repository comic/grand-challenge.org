from urllib.parse import urlencode

from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.template.defaultfilters import linebreaksbr
from django.utils.html import format_html

from grandchallenge.components.admin import ComponentImageAdmin
from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstations.models import (
    Feedback,
    FeedbackGroupObjectPermission,
    FeedbackUserObjectPermission,
    Session,
    SessionGroupObjectPermission,
    SessionUserObjectPermission,
    Workstation,
    WorkstationGroupObjectPermission,
    WorkstationImage,
    WorkstationImageGroupObjectPermission,
    WorkstationImageUserObjectPermission,
    WorkstationUserObjectPermission,
)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = [
        "pk",
        "created",
        "maximum_duration",
        "status",
        "creator",
        "region",
        "ping_times",
        "extra_env_vars",
        "get_reader_studies",
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
        "extra_env_vars",
    ]
    search_fields = [
        "pk",
        "creator__username",
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("reader_studies")

    @admin.display(description="Reader Studies")
    def get_reader_studies(self, obj):
        return linebreaksbr(
            "\n".join(r.slug for r in obj.reader_studies.all())
        )


@admin.register(Feedback)
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
admin.site.register(WorkstationUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(
    WorkstationGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(WorkstationImage, ComponentImageAdmin)
admin.site.register(
    WorkstationImageUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    WorkstationImageGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(SessionUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(SessionGroupObjectPermission, GroupObjectPermissionAdmin)
admin.site.register(FeedbackUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(FeedbackGroupObjectPermission, GroupObjectPermissionAdmin)
