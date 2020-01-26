from django.contrib import admin

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    Job,
    Result,
)
from grandchallenge.evaluation.templatetags.evaluation_extras import user_error


class JobAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = (
        "pk",
        "created",
        "algorithm",
        "creator",
        "status",
        "error_message",
    )
    list_select_related = ("algorithm_image__algorithm",)
    list_filter = ("status",)
    readonly_fields = (
        "image",
        "creator",
        "algorithm_image",
    )
    search_fields = (
        "creator__username",
        "pk",
        "output",
        "algorithm_image__algorithm__title",
    )

    def algorithm(self, obj):
        return obj.algorithm_image.algorithm

    def error_message(self, obj):
        return user_error(obj.output)


admin.site.register(Algorithm)
admin.site.register(AlgorithmImage)
admin.site.register(Job, JobAdmin)
admin.site.register(Result)
