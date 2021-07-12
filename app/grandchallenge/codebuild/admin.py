from django.contrib import admin

from grandchallenge.codebuild.models import Build


class BuildAdmin(admin.ModelAdmin):
    readonly_fields = (
        "status",
        "build_id",
        "build_log",
        "build_config",
        "algorithm_image",
        "webhook_message",
    )
    list_display = ("pk", "build_id", "created", "status", "algorithm_image")
    ordering = ("-created",)
    list_filter = ("status", "algorithm_image__algorithm__slug")
    list_select_related = ("algorithm_image__algorithm",)


admin.site.register(Build, BuildAdmin)
