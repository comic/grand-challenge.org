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
        "ready",
        "image_sha256",
        "requires_gpu",
        "requires_memory_gb",
        "status",
    )
    list_filter = ("ready", "requires_gpu")
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

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("store_in_database", *self.readonly_fields)
        else:
            return self.readonly_fields


class ComponentInterfaceValueAdmin(admin.ModelAdmin):
    list_display = ("pk", "interface", "value", "file", "image")
    readonly_fields = ("interface", "value", "file", "image")


admin.site.register(ComponentInterface, ComponentInterfaceAdmin)
admin.site.register(ComponentInterfaceValue, ComponentInterfaceValueAdmin)


def requeue_jobs(modeladmin, request, queryset):
    queryset.update(status=ComponentJob.RETRY)
    for job in queryset:
        on_commit(job.execute)


requeue_jobs.short_description = "Requeue selected jobs"
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
