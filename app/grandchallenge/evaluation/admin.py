from django.contrib import admin

from grandchallenge.evaluation.models import (
    Config,
    Evaluation,
    Method,
    Submission,
)


class ConfigAdmin(admin.ModelAdmin):
    ordering = ("challenge",)
    list_display = ("pk", "challenge", "modified")
    search_fields = ("pk",)


class MethodAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = ("pk", "created", "challenge", "ready", "status")
    list_filter = ("challenge__short_name",)
    search_fields = ("pk",)
    readonly_fields = ("creator", "challenge")


class SubmissionAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = ("pk", "created", "challenge", "creator")
    list_filter = ("challenge__short_name",)
    search_fields = (
        "pk",
        "creator__username",
    )
    readonly_fields = (
        "creator",
        "challenge",
        "file",
    )


class JobAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = ("pk", "created", "challenge", "creator", "status")
    list_filter = ("submission__challenge__short_name", "status")
    list_select_related = ("submission__challenge", "submission__creator")
    search_fields = (
        "pk",
        "submission__pk",
        "submission__challenge__short_name",
        "submission__creator__username",
    )
    readonly_fields = ("status", "submission", "method")


admin.site.register(Config, ConfigAdmin)
admin.site.register(Method, MethodAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(Evaluation, JobAdmin)
