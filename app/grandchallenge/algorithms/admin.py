from django.contrib import admin
from django.db.models import Count
from django.db.transaction import on_commit
from guardian.admin import GuardedModelAdmin

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmPermissionRequest,
    Job,
)
from grandchallenge.components.admin import ComponentImageAdmin
from grandchallenge.components.tasks import deprovision_job


class AlgorithmAdmin(GuardedModelAdmin):
    list_display = (
        "title",
        "created",
        "public",
        "credits_per_job",
        "average_duration",
        "container_count",
    )
    list_filter = (
        "public",
        "use_flexible_inputs",
    )

    def container_count(self, obj):
        return obj.container_count

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            container_count=Count("algorithm_container_images")
        )
        return queryset


def requeue_jobs(modeladmin, request, queryset):
    """
    Retries the selected jobs.

    Note that any linked task will not be executed.
    """
    queryset.update(status=Job.RETRY)
    for job in queryset:
        on_commit(job.execute)


requeue_jobs.short_description = "Requeue selected jobs"
requeue_jobs.allowed_permissions = ("change",)


def cancel_jobs(modeladmin, request, queryset):
    queryset.filter(
        status__in=[Job.PENDING, Job.PROVISIONED, Job.EXECUTING, Job.RETRY]
    ).update(status=Job.CANCELLED)


cancel_jobs.short_description = "Cancel selected jobs"
cancel_jobs.allowed_permissions = ("change",)


def deprovision_jobs(modeladmin, request, queryset):
    for job in queryset:
        deprovision_job.signature(**job.signature_kwargs).apply_async()


deprovision_jobs.short_description = "Deprovision jobs"
deprovision_jobs.allowed_permissions = ("change",)


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
        "task_on_success",
        "task_on_failure",
    )
    search_fields = (
        "creator__username",
        "pk",
        "algorithm_image__algorithm__slug",
    )
    actions = (requeue_jobs, cancel_jobs, deprovision_jobs)

    def algorithm(self, obj):
        return obj.algorithm_image.algorithm


class AlgorithmPermissionRequestAdmin(GuardedModelAdmin):
    readonly_fields = (
        "user",
        "algorithm",
    )


admin.site.register(Algorithm, AlgorithmAdmin)
admin.site.register(AlgorithmImage, ComponentImageAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(
    AlgorithmPermissionRequest, AlgorithmPermissionRequestAdmin
)
