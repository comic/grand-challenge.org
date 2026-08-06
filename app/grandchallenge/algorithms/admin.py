import humanize
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Sum
from django.utils.html import format_html

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmAlgorithmInterface,
    AlgorithmGroupObjectPermission,
    AlgorithmImage,
    AlgorithmImageGroupObjectPermission,
    AlgorithmImageUserObjectPermission,
    AlgorithmInterface,
    AlgorithmModel,
    AlgorithmModelGroupObjectPermission,
    AlgorithmModelUserObjectPermission,
    AlgorithmPermissionRequest,
    AlgorithmUserCredit,
    AlgorithmUserObjectPermission,
    Endpoint,
    EndpointGroupObjectPermission,
    EndpointUserObjectPermission,
    Invocation,
    Job,
    JobGroupObjectPermission,
    JobUserObjectPermission,
)
from grandchallenge.components.admin import (
    ComponentImageAdmin,
    cancel_jobs,
    deprovision_jobs,
    requeue_jobs,
    stop_endpoints,
)
from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.core.templatetags.costs import millicents_to_euro
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.subdomains.utils import reverse
from grandchallenge.utilization.models import JobUtilization


@admin.register(Algorithm)
class AlgorithmAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    readonly_fields = ("public", "algorithm_interfaces_configuration_link")
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

    actions = ["unpublish_algorithms"]

    def container_count(self, obj):
        return obj.container_count

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            container_count=Count("algorithm_container_images")
        )
        return queryset

    @admin.action(
        description="Unpublish selected algorithms", permissions=("change",)
    )
    def unpublish_algorithms(self, request, queryset):
        for algorithm in queryset:
            algorithm.public = False
            algorithm.save()

        self.message_user(
            request, f"{len(queryset)} algorithm(s) unpublished."
        )

    @staticmethod
    def algorithm_interfaces_configuration_link(obj):
        return format_html(
            "<a target=_blank href='{url}'>🔗</a>",
            url=reverse(
                "algorithms:interface-list",
                kwargs={"slug": obj.slug},
            ),
        )


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
            JobUtilization.objects.filter(
                algorithm=obj.algorithm,
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
            JobUtilization.objects.filter(
                creator=obj.user,
            )
            .exclude(algorithm=obj.algorithm)
            .aggregate(
                total=Sum("compute_cost_euro_millicents", default=0),
            )["total"]
        )


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    autocomplete_fields = ("viewer_groups",)
    ordering = ("-created",)
    list_display = (
        "pk",
        "external_admin",
        "created",
        "algorithm",
        "creator",
        "is_complimentary",
        "credits_consumed",
        "time_limit",
        "exec_duration",
        "requires_gpu_type",
        "requires_memory_gb",
        "use_warm_pool",
        "status",
        "public",
        "comment",
        "error_message",
    )
    list_select_related = ("algorithm_image__algorithm",)
    list_filter = (
        "status",
        "public",
        "is_complimentary",
        "requires_gpu_type",
        "use_warm_pool",
    )
    readonly_fields = (
        "creator",
        "algorithm_image",
        "inputs",
        "outputs",
        "viewers",
        "attempt",
        "error_message",
        "detailed_error_message",
        "input_prefixes",
        "task_on_success",
        "task_on_failure",
        "algorithm_interface",
        "time_limit",
        "exec_duration",
        "invoke_duration",
        "job_utilization",
        "public",
        "algorithm_model",
        "status",
        "viewer_groups",
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

    def external_admin(self, obj):
        executor = obj.get_executor(
            backend=settings.COMPONENTS_DEFAULT_BACKEND
        )
        return format_html(
            "<a target=_blank href='{url}'>🔗</a>",
            url=executor.external_admin_url,
        )


@admin.register(AlgorithmPermissionRequest)
class AlgorithmPermissionRequestAdmin(admin.ModelAdmin):
    readonly_fields = ("user", "algorithm")


@admin.register(AlgorithmModel)
class AlgorithmModelAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = (
        "algorithm",
        "created",
        "is_desired_version",
        "comment",
        "naturalsize_in_storage",
    )
    list_filter = ("is_desired_version",)
    search_fields = ("algorithm__title", "comment")
    readonly_fields = (
        "creator",
        "algorithm",
        "checksum",
        "size_in_storage",
        "user_upload",
        "import_status",
        "model",
    )

    @admin.display(ordering="size_in_storage")
    def naturalsize_in_storage(self, obj):
        return humanize.naturalsize(obj.size_in_storage)


@admin.register(AlgorithmInterface)
class AlgorithmInterfaceAdmin(admin.ModelAdmin):
    readonly_fields = ("algorithm_inputs", "algorithm_outputs")
    list_display = (
        "pk",
        "algorithm_inputs",
        "algorithm_outputs",
    )
    search_fields = (
        "pk",
        "inputs__slug",
        "outputs__slug",
    )

    def algorithm_inputs(self, obj):
        return oxford_comma(obj.inputs.all())

    def algorithm_outputs(self, obj):
        return oxford_comma(obj.outputs.all())

    def has_change_permission(self, request, obj=None):
        # interfaces cannot be modified
        return False

    def has_delete_permission(self, request, obj=None):
        # interfaces cannot be deleted
        return False

    def has_add_permission(self, request, obj=None):
        # interfaces should only be created through the UI
        return False


@admin.register(AlgorithmAlgorithmInterface)
class AlgorithmAlgorithmInterfaceAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "algorithm",
    )
    list_filter = ("algorithm",)

    def has_add_permission(self, request, obj=None):
        # through table entries should only be created through the UI
        return False

    def has_change_permission(self, request, obj=None):
        # through table entries should only be updated through the UI
        return False

    def has_delete_permission(self, request, obj=None):
        # through table entries should only be deleted through the UI
        return False


@admin.register(AlgorithmImage)
class AlgorithmImageAdmin(ComponentImageAdmin):
    readonly_fields = (*ComponentImageAdmin.readonly_fields, "algorithm")


@admin.register(Endpoint)
class EndpointAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "created",
        "algorithm",
        "creator",
        "maximum_duration",
        "requires_gpu_type",
        "requires_memory_gb",
        "status",
    )
    list_select_related = ("algorithm_image__algorithm",)
    list_filter = ("status",)
    search_fields = (
        "creator__username",
        "pk",
        "algorithm_image__algorithm__slug",
        "algorithm_image__pk",
    )
    readonly_fields = (
        "created",
        "modified",
        "algorithm_image",
        "algorithm_model",
        "creator",
        "maximum_duration",
        "status",
        "error_message",
        "requires_gpu_type",
        "requires_memory_gb",
        "viewers_group",
    )
    actions = (stop_endpoints,)

    @staticmethod
    def algorithm(obj):
        return obj.algorithm_image.algorithm

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Invocation)
class InvocationAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "created",
        "endpoint",
        "time_limit",
        "invoke_duration",
        "status",
    )
    list_filter = ("status",)
    search_fields = (
        "pk",
        "endpoint__pk",
    )
    readonly_fields = (
        "invoke_duration",
        "error_message",
        "detailed_error_message",
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(AlgorithmUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(AlgorithmGroupObjectPermission, GroupObjectPermissionAdmin)
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
admin.site.register(EndpointUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(EndpointGroupObjectPermission, GroupObjectPermissionAdmin)
