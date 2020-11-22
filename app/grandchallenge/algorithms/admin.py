from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmPermissionRequest,
    Job,
)


class AlgorithmImageAdmin(GuardedModelAdmin):
    exclude = ("image",)


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
    )
    search_fields = (
        "creator__username",
        "pk",
        "algorithm_image__algorithm__slug",
    )

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
