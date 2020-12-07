from django.contrib import admin

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


class MethodAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = ("pk", "created", "phase", "ready", "status")
    list_filter = ("phase__challenge__short_name",)
    search_fields = ("pk",)
    readonly_fields = ("creator", "phase")
    exclude = ("image",)


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
        "creators_ip",
        "creators_user_agent",
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
    )


admin.site.register(Phase, PhaseAdmin)
admin.site.register(Method, MethodAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(Evaluation, EvaluationAdmin)
