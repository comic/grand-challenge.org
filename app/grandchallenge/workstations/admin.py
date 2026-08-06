from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.template.defaultfilters import linebreaksbr
from django.utils.html import format_html
from django.utils.timezone import now

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
        "get_logs",
        "get_metrics",
        "creator",
        "created",
        "claimed_at",
        "status",
        "maximum_duration",
        "region",
        "host_address",
        "http_port",
        "websocket_port",
        "ping_times",
        "extra_env_vars",
        "get_reader_studies",
    ]
    list_filter = ["status", "region", "workstation_image__workstation__slug"]
    readonly_fields = [
        "creator",
        "workstation_image",
        "status",
        "task_arn",
        "host_address",
        "http_port",
        "websocket_port",
        "region",
        "ping_times",
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

    @admin.display(description="Logs")
    def get_logs(self, obj):
        if obj.task_arn:
            task_id = obj.task_arn.split("/")[-1]
            return format_html(
                "<a target=_blank href='https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#logsV2:log-groups/log-group/{log_group}/log-events/ecs$252Fworkstation$252F{task_id}'>🔗</a>",
                region=obj.region,
                log_group=settings.COMPONENTS_SERVICE_LOG_GROUP_NAME,
                task_id=task_id,
            )
        else:
            return None

    @admin.display(description="Metrics")
    def get_metrics(self, obj):
        if obj.task_arn:
            task_id = obj.task_arn.split("/")[-1]
            start = obj.created.strftime("%Y-%m-%dT%H*3a%M*3a%S.000Z")

            if obj.claimed_at:
                end_time = obj.claimed_at + obj.maximum_duration
            else:
                end_time = obj.created + timedelta(
                    hours=settings.WORKSTATIONS_MAXIMUM_UNCLAIMED_SESSION_HOURS
                )

            end_time += timedelta(minutes=settings.WORKSTATIONS_GRACE_MINUTES)
            end_time = min(now(), end_time)

            end = end_time.strftime("%Y-%m-%dT%H*3a%M*3a%S.000Z")

            return format_html(
                "<a target=_blank href=\"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#container-insights:performance/ECS:Task:Granular?~(query~(controls~(CW*3a*3aECS.cluster~(~'{cluster_name})~CW*3a*3aECS.taskId~(~'{task_id})))~context~(orchestrationService~'ecs~timeRange~(end~'{end}~start~'{start})))\">🔗</a>",
                region=obj.region,
                cluster_name=settings.COMPONENTS_SERVICE_CLUSTER_NAME,
                task_id=task_id,
                end=end,
                start=start,
            )
        else:
            return None


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
            '<a href="https://github.com/diagnijmegen/rse-cirrus-core/issues/new?{query}">Create issue</a>',
            query=urlencode(params),
        )


@admin.register(WorkstationImage)
class WorkstationImageAdmin(ComponentImageAdmin):
    readonly_fields = (
        *ComponentImageAdmin.readonly_fields,
        "image",
        "workstation",
    )


@admin.register(Workstation)
class WorkstationAdmin(admin.ModelAdmin):
    search_fields = ("title", "slug")


admin.site.register(WorkstationUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(
    WorkstationGroupObjectPermission, GroupObjectPermissionAdmin
)
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
