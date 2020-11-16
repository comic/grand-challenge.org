from django.contrib import admin

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmPermissionRequest,
    Job,
)
from grandchallenge.evaluation.templatetags.evaluation_extras import user_error


class AlgorithmImageAdmin(admin.ModelAdmin):
    exclude = ("image",)


class JobAdmin(admin.ModelAdmin):
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
    )
    search_fields = (
        "creator__username",
        "pk",
        "output",
        "algorithm_image__algorithm__slug",
    )

    def algorithm(self, obj):
        return obj.algorithm_image.algorithm

    def error_message(self, obj):
        return user_error(obj.output)


class AlgorithmPermissionRequestAdmin(admin.ModelAdmin):
    readonly_fields = (
        "user",
        "algorithm",
    )


admin.site.register(Algorithm)
admin.site.register(AlgorithmImage, AlgorithmImageAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(
    AlgorithmPermissionRequest, AlgorithmPermissionRequestAdmin
)
