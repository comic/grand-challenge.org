from django.contrib import admin
from django.db.models import Count
from django.forms import ModelForm
from guardian.admin import GuardedModelAdmin

from grandchallenge.algorithms.forms import AlgorithmIOValidationMixin
from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmGroupObjectPermission,
    AlgorithmImage,
    AlgorithmImageGroupObjectPermission,
    AlgorithmImageUserObjectPermission,
    AlgorithmPermissionRequest,
    AlgorithmUserObjectPermission,
    Job,
    JobGroupObjectPermission,
    JobUserObjectPermission,
)
from grandchallenge.components.admin import (
    ComponentImageAdmin,
    cancel_jobs,
    deprovision_jobs,
    requeue_jobs,
)
from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)


class AlgorithmAdminForm(AlgorithmIOValidationMixin, ModelForm):
    class Meta:
        model = Algorithm
        fields = "__all__"


@admin.register(Algorithm)
class AlgorithmAdmin(GuardedModelAdmin):
    list_display = (
        "title",
        "created",
        "public",
        "credits_per_job",
        "average_duration",
        "container_count",
        "workstation",
    )
    list_filter = ("public", "workstation__slug")
    search_fields = ("title", "slug")
    readonly_fields = ("credits_per_job",)
    form = AlgorithmAdminForm

    def container_count(self, obj):
        return obj.container_count

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            container_count=Count("algorithm_container_images")
        )
        return queryset


@admin.register(Job)
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
    list_filter = ("status", "public")
    readonly_fields = (
        "creator",
        "algorithm_image",
        "inputs",
        "outputs",
        "viewers",
        "attempt",
        "stdout",
        "stderr",
        "error_message",
        "input_prefixes",
        "task_on_success",
        "task_on_failure",
        "runtime_metrics",
    )
    search_fields = (
        "creator__username",
        "pk",
        "algorithm_image__algorithm__slug",
        "algorithm_image__pk",
    )
    actions = (requeue_jobs, cancel_jobs, deprovision_jobs)

    def algorithm(self, obj):
        return obj.algorithm_image.algorithm


@admin.register(AlgorithmPermissionRequest)
class AlgorithmPermissionRequestAdmin(GuardedModelAdmin):
    readonly_fields = ("user", "algorithm")


admin.site.register(AlgorithmUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(AlgorithmGroupObjectPermission, GroupObjectPermissionAdmin)
admin.site.register(AlgorithmImage, ComponentImageAdmin)
admin.site.register(
    AlgorithmImageUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    AlgorithmImageGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(JobUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(JobGroupObjectPermission, GroupObjectPermissionAdmin)
