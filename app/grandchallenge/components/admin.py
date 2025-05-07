from django.contrib import admin
from django.db.transaction import on_commit
from guardian.admin import GuardedModelAdmin

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceExampleValue,
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
        "import_status",
        "sha256_display",
        "status",
        "latest_shimmed_version",
        "is_desired_version",
        "is_removed",
    )
    list_filter = (
        "is_manifest_valid",
        "is_in_registry",
        "import_status",
        "is_desired_version",
        "is_removed",
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
    readonly_fields = ("example_value",)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("store_in_database", *self.readonly_fields)
        else:
            return self.readonly_fields


@admin.register(ComponentInterfaceExampleValue)
class ComponentInterfaceExampleValueAdmin(admin.ModelAdmin):
    list_display = ("pk", "interface", "value", "extra_info")
    search_fields = ("interface__slug",)


@admin.register(ComponentInterfaceValue)
class ComponentInterfaceValueAdmin(admin.ModelAdmin):
    list_display = ("pk", "interface", "value", "file", "image")
    readonly_fields = ("interface", "value", "file", "image")
    list_filter = ("interface",)
    search_fields = (
        "pk",
        "file",
        "value",
        "image__name",
    )


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
        job.started_at = None
        job.completed_at = None
        job.error_message = ""
        job.detailed_error_message = {}
        jobs.append(job)

        on_commit(job.execute)

    queryset.model.objects.bulk_update(
        jobs,
        fields=[
            "status",
            "attempt",
            "started_at",
            "completed_at",
            "error_message",
            "detailed_error_message",
        ],
    )


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
            ComponentJob.EXECUTING_PREREQUISITES,
            ComponentJob.VALIDATING_INPUTS,
        ]
    ).select_for_update(of=("self",), skip_locked=True).update(
        status=ComponentJob.CANCELLED
    )


@admin.action(
    description="Deprovision jobs",
    permissions=("change",),
)
def deprovision_jobs(modeladmin, request, queryset):
    for job in queryset:
        deprovision_job.signature(**job.signature_kwargs).apply_async()
