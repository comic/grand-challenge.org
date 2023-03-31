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
        "import_status",
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
        "import_status",
    )
    search_fields = ("pk", "creator__username", "image_sha256")


@admin.register(ComponentInterface)
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


@admin.register(ComponentInterfaceValue)
class ComponentInterfaceValueAdmin(admin.ModelAdmin):
    list_display = ("pk", "interface", "value", "file", "image")
    readonly_fields = ("interface", "value", "file", "image")
    list_filter = ("interface",)


@admin.action(
    description="Requeue selected Failed/Cancelled jobs",
    permissions=("change",),
)
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


@admin.action(
    description="Cancel selected jobs",
    permissions=("change",),
)
def cancel_jobs(modeladmin, request, queryset):
    queryset.filter(
        status__in=[
            ComponentJob.PENDING,
            ComponentJob.PROVISIONED,
            ComponentJob.EXECUTING,
            ComponentJob.EXECUTED,
            ComponentJob.PARSING,
            ComponentJob.RETRY,
        ]
    ).update(status=ComponentJob.CANCELLED)


@admin.action(
    description="Deprovision jobs",
    permissions=("change",),
)
def deprovision_jobs(modeladmin, request, queryset):
    for job in queryset:
        deprovision_job.signature(**job.signature_kwargs).apply_async()
