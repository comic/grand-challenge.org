import json

from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Sum
from django.forms import ModelForm
from django.utils.html import format_html
from guardian.admin import GuardedModelAdmin

from grandchallenge.algorithms.forms import AlgorithmIOValidationMixin
from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmGroupObjectPermission,
    AlgorithmImage,
    AlgorithmImageGroupObjectPermission,
    AlgorithmImageUserObjectPermission,
    AlgorithmModel,
    AlgorithmModelGroupObjectPermission,
    AlgorithmModelUserObjectPermission,
    AlgorithmPermissionRequest,
    AlgorithmUserCredit,
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
from grandchallenge.core.templatetags.costs import millicents_to_euro
from grandchallenge.core.utils.grand_challenge_forge import (
    get_forge_algorithm_template_context,
)


class AlgorithmAdminForm(AlgorithmIOValidationMixin, ModelForm):
    class Meta:
        model = Algorithm
        fields = "__all__"


@admin.register(Algorithm)
class AlgorithmAdmin(GuardedModelAdmin):
    readonly_fields = ("algorithm_forge_json",)
    list_display = (
        "title",
        "created",
        "public",
        "time_limit",
        "job_requires_gpu_type",
        "job_requires_memory_gb",
        "average_duration",
        "container_count",
        "workstation",
    )
    list_filter = ("public", "job_requires_gpu_type", "workstation__slug")
    search_fields = ("title", "slug")
    form = AlgorithmAdminForm

    def container_count(self, obj):
        return obj.container_count

    @staticmethod
    def algorithm_forge_json(obj):
        json_desc = get_forge_algorithm_template_context(algorithm=obj)
        return format_html(
            "<pre>{json_desc}</pre>", json_desc=json.dumps(json_desc, indent=2)
        )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            container_count=Count("algorithm_container_images")
        )
        return queryset


@admin.register(AlgorithmUserCredit)
class AlgorithmUserCreditAdmin(ModelAdmin):
    list_display = (
        "user",
        "algorithm",
        "credits",
        "valid_from",
        "valid_until",
        "is_active",
        "comment",
    )
    autocomplete_fields = ("user", "algorithm")
    search_fields = ("user__username", "user__email", "algorithm__slug")
    fields = (
        "user",
        "algorithm",
        "credits",
        "valid_from",
        "valid_until",
        "comment",
    )
    readonly_fields = (
        "is_active",
        "remaining_specific_credits",
        "remaining_general_credits",
        "specific_compute_costs",
        "other_compute_costs",
    )

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)

        if obj:
            fields += (
                "is_active",
                "remaining_specific_credits",
                "remaining_general_credits",
                "specific_compute_costs",
                "other_compute_costs",
            )

        return fields

    @admin.display(
        description="The remaining specific credits for this algorithm for this User"
    )
    def remaining_specific_credits(self, obj):
        try:
            return AlgorithmImage.get_remaining_specific_credits(
                user=obj.user, algorithm=obj.algorithm
            )
        except ObjectDoesNotExist:
            return 0

    @admin.display(description="The remaining general credits for this User")
    def remaining_general_credits(self, obj):
        return AlgorithmImage.get_remaining_general_credits(user=obj.user)

    @admin.display(
        description="Total compute costs for this algorithm by this User"
    )
    def specific_compute_costs(self, obj):
        return millicents_to_euro(
            Job.objects.filter(
                algorithm_image__algorithm=obj.algorithm,
                creator=obj.user,
            ).aggregate(
                total=Sum("compute_cost_euro_millicents", default=0),
            )[
                "total"
            ]
        )

    @admin.display(
        description="Total compute costs for all other algorithms by this User"
    )
    def other_compute_costs(self, obj):
        return millicents_to_euro(
            Job.objects.filter(
                creator=obj.user,
            )
            .exclude(algorithm_image__algorithm=obj.algorithm)
            .aggregate(
                total=Sum("compute_cost_euro_millicents", default=0),
            )["total"]
        )


@admin.register(Job)
class JobAdmin(GuardedModelAdmin):
    autocomplete_fields = ("viewer_groups",)
    ordering = ("-created",)
    list_display = (
        "pk",
        "created",
        "algorithm",
        "creator",
        "is_complimentary",
        "credits_consumed",
        "compute_cost_euro_millicents",
        "time_limit",
        "requires_gpu_type",
        "requires_memory_gb",
        "status",
        "public",
        "comment",
        "error_message",
    )
    list_select_related = ("algorithm_image__algorithm",)
    list_filter = ("status", "public", "is_complimentary", "requires_gpu_type")
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
        "detailed_error_message",
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


@admin.register(AlgorithmModel)
class AlgorithmModelAdmin(GuardedModelAdmin):
    exclude = ("model",)
    list_display = ("algorithm", "created", "is_desired_version", "comment")
    list_filter = ("is_desired_version",)
    search_fields = ("algorithm__title", "comment")
    readonly_fields = ("creator", "algorithm", "sha256", "size_in_storage")


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
admin.site.register(
    AlgorithmModelUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    AlgorithmModelGroupObjectPermission, GroupObjectPermissionAdmin
)
