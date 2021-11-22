from django.contrib import admin

from grandchallenge.components.admin import (
    ComponentImageAdmin,
    cancel_jobs,
    deprovision_jobs,
    requeue_jobs,
)
from grandchallenge.evaluation.models import (
    Evaluation,
    Method,
    Phase,
    Submission,
)


class PhaseAdmin(admin.ModelAdmin):
    ordering = ("challenge",)
    list_display = ("pk", "challenge", "title", "slug", "modified")
    search_fields = ("pk",)


class SubmissionAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = ("pk", "created", "phase", "creator")
    list_filter = ("phase__challenge__short_name",)
    search_fields = (
        "pk",
        "creator__username",
    )
    readonly_fields = (
        "creator",
        "phase",
        "predictions_file",
        "algorithm_image",
    )


class EvaluationAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = ("pk", "created", "submission", "status", "error_message")
    list_filter = ("submission__phase__challenge__short_name", "status")
    list_select_related = (
        "submission__phase__challenge",
        "submission__creator",
    )
    search_fields = (
        "pk",
        "submission__pk",
        "submission__phase__challenge__short_name",
        "submission__creator__username",
    )
    readonly_fields = (
        "status",
        "submission",
        "method",
        "inputs",
        "outputs",
        "stdout",
        "stderr",
        "error_message",
        "input_prefixes",
        "task_on_success",
        "task_on_failure",
    )
    actions = (requeue_jobs, cancel_jobs, deprovision_jobs)


admin.site.register(Phase, PhaseAdmin)
admin.site.register(Method, ComponentImageAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(Evaluation, EvaluationAdmin)
