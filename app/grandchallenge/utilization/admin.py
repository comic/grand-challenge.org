from django.contrib import admin

from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.utilization.models import (
    EvaluationUtilization,
    JobUtilization,
    JobWarmPoolUtilization,
    SessionUtilization,
)


@admin.register(SessionUtilization)
class SessionUtilizationAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = (
        "pk",
        "created",
        "session",
        "creator",
        "duration",
        "credits_consumed",
        "accessed_reader_studies",
    )
    search_fields = (
        "creator__username",
        "pk",
        "reader_studies__slug",
        "reader_studies__pk",
    )
    readonly_fields = ("reader_studies", "credits_consumed")

    def accessed_reader_studies(self, obj):
        return oxford_comma(obj.reader_studies.all())


@admin.register(JobUtilization)
class JobUtilizationAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = (
        "pk",
        "created",
        "job",
        "creator",
        "duration",
        "compute_cost_euro_millicents",
        "phase",
        "challenge",
        "algorithm_image",
        "algorithm",
    )
    search_fields = (
        "creator__username",
        "pk",
        "job__pk",
        "phase__slug",
        "challenge__short_name",
    )
    readonly_fields = (
        "creator",
        "phase",
        "challenge",
        "archive",
        "algorithm_image",
        "algorithm",
        "duration",
        "compute_cost_euro_millicents",
        "job",
    )


@admin.register(JobWarmPoolUtilization)
class JobWarmPoolUtilizationAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = (
        "pk",
        "created",
        "job",
        "creator",
        "duration",
        "compute_cost_euro_millicents",
        "phase",
        "challenge",
        "algorithm_image",
        "algorithm",
    )
    search_fields = (
        "creator__username",
        "pk",
        "job__pk",
        "phase__slug",
        "challenge__short_name",
    )
    readonly_fields = (
        "creator",
        "phase",
        "challenge",
        "archive",
        "algorithm_image",
        "algorithm",
        "duration",
        "compute_cost_euro_millicents",
        "job",
    )


@admin.register(EvaluationUtilization)
class EvaluationUtilizationAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_filter = ("external_evaluation",)
    list_display = (
        "pk",
        "created",
        "evaluation",
        "external_evaluation",
        "creator",
        "duration",
        "compute_cost_euro_millicents",
        "phase",
        "challenge",
        "algorithm_image",
        "algorithm",
    )
    search_fields = (
        "creator__username",
        "pk",
        "evaluation__pk",
        "phase__slug",
        "challenge__short_name",
    )
    readonly_fields = (
        "creator",
        "phase",
        "challenge",
        "archive",
        "algorithm_image",
        "algorithm",
        "duration",
        "compute_cost_euro_millicents",
        "evaluation",
    )
