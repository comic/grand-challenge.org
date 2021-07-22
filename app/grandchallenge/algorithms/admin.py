from django.contrib import admin
from django.db.transaction import on_commit
from guardian.admin import GuardedModelAdmin

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmPermissionRequest,
    Job,
)


class AlgorithmImageAdmin(GuardedModelAdmin):
    exclude = ("image",)


def requeue_jobs(modeladmin, request, queryset):
    """
    Retries the selected jobs.

    Note that any linked task will not be executed.
    """
    queryset.update(status=Job.RETRY)
    for job in queryset:
        on_commit(job.signature.apply_async)


requeue_jobs.short_description = "Requeue selected jobs"
requeue_jobs.allowed_permissions = ("change",)


class JobAdmin(GuardedModelAdmin):
    autocomplete_fields = ("viewer_groups",)
    ordering = ("-created",)
    list_display = (
        "pk",
        "created",
        "algorithm",
        "creator",
        "status",
        "public",
        "comment",
        "error_message",
    )
    list_select_related = ("algorithm_image__algorithm",)
    list_filter = (
        "status",
        "public",
    )
    readonly_fields = (
        "creator",
        "algorithm_image",
        "inputs",
        "outputs",
        "viewers",
        "stdout",
        "stderr",
        "error_message",
        "input_prefixes",
    )
    search_fields = (
        "creator__username",
        "pk",
        "algorithm_image__algorithm__slug",
    )
    actions = (requeue_jobs,)

    def algorithm(self, obj):
        return obj.algorithm_image.algorithm


class AlgorithmPermissionRequestAdmin(GuardedModelAdmin):
    readonly_fields = (
        "user",
        "algorithm",
    )


admin.site.register(Algorithm, GuardedModelAdmin)
admin.site.register(AlgorithmImage, AlgorithmImageAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(
    AlgorithmPermissionRequest, AlgorithmPermissionRequestAdmin
)
