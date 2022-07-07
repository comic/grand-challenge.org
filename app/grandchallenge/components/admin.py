from django.contrib import admin
from django.db.transaction import on_commit
from guardian.admin import GuardedModelAdmin

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    ComponentJob,
)
from grandchallenge.components.tasks import deprovision_job


class ComponentImageAdmin(GuardedModelAdmin):
    exclude = ("image",)
    readonly_fields = ("creator",)
    list_display = (
        "pk",
        "created",
        "creator",
        "is_manifest_valid",
        "is_in_registry",
        "is_on_sagemaker",
        "image_sha256",
        "requires_gpu",
        "requires_memory_gb",
        "status",
        "latest_shimmed_version",
    )
    list_filter = (
        "requires_gpu",
        "is_manifest_valid",
        "is_in_registry",
        "is_on_sagemaker",
    )
    search_fields = ("pk", "creator__username", "image_sha256")


class ComponentInterfaceAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "title",
        "slug",
        "kind",
        "default_value",
        "relative_path",
        "schema",
        "store_in_database",
    )
    search_fields = ("title", "slug")
    list_filter = ("kind",)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("store_in_database", *self.readonly_fields)
        else:
            return self.readonly_fields


class ComponentInterfaceValueAdmin(admin.ModelAdmin):
    list_display = ("pk", "interface", "value", "file", "image")
    readonly_fields = ("interface", "value", "file", "image")
    list_filter = ("interface",)


admin.site.register(ComponentInterface, ComponentInterfaceAdmin)
admin.site.register(ComponentInterfaceValue, ComponentInterfaceValueAdmin)


def requeue_jobs(modeladmin, request, queryset):
    queryset = queryset.filter(
        status__in=[
            ComponentJob.FAILURE,
            ComponentJob.CANCELLED,
        ]
    )

    jobs = []

    for job in queryset:
        job.status = ComponentJob.RETRY
        job.attempt += 1
        jobs.append(job)

        on_commit(job.execute)

    queryset.model.objects.bulk_update(jobs, fields=["status", "attempt"])


requeue_jobs.short_description = "Requeue selected Failed/Cancelled jobs"
requeue_jobs.allowed_permissions = ("change",)


def cancel_jobs(modeladmin, request, queryset):
    queryset.filter(
        status__in=[
            ComponentJob.PENDING,
            ComponentJob.PROVISIONED,
            ComponentJob.EXECUTING,
            ComponentJob.RETRY,
        ]
    ).update(status=ComponentJob.CANCELLED)


cancel_jobs.short_description = "Cancel selected jobs"
cancel_jobs.allowed_permissions = ("change",)


def deprovision_jobs(modeladmin, request, queryset):
    for job in queryset:
        deprovision_job.signature(**job.signature_kwargs).apply_async()


deprovision_jobs.short_description = "Deprovision jobs"
deprovision_jobs.allowed_permissions = ("change",)
