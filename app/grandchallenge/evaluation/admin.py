from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import ModelForm

from grandchallenge.components.admin import (
    ComponentImageAdmin,
    cancel_jobs,
    deprovision_jobs,
    requeue_jobs,
)
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.evaluation.models import (
    Evaluation,
    Method,
    Phase,
    Submission,
)
from grandchallenge.evaluation.tasks import create_evaluation


class PhaseAdminForm(ModelForm):
    class Meta:
        model = Phase
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        duplicate_interfaces = {
            *cleaned_data.get("algorithm_inputs", [])
        }.intersection({*cleaned_data.get("algorithm_outputs", [])})

        if duplicate_interfaces:
            raise ValidationError(
                f"The sets of Algorithm Inputs and Algorithm Outputs must be unique: "
                f"{oxford_comma(duplicate_interfaces)} present in both"
            )

        return cleaned_data


class PhaseAdmin(admin.ModelAdmin):
    ordering = ("challenge",)
    list_display = (
        "slug",
        "title",
        "challenge",
        "submission_kind",
        "open_for_submissions",
        "submissions_open_at",
        "submissions_close_at",
        "submission_limit",
    )
    search_fields = ("pk", "title", "slug", "challenge__short_name")
    list_filter = (
        "submission_kind",
        "challenge__short_name",
    )
    form = PhaseAdminForm

    @admin.display(boolean=True)
    def open_for_submissions(self, instance):
        return instance.open_for_submissions


def reevaluate_submissions(modeladmin, request, queryset):
    """Creates a new evaluation for an existing submission"""
    for submission in queryset:
        create_evaluation.apply_async(
            kwargs={"submission_pk": str(submission.pk)}
        )


reevaluate_submissions.short_description = "Reevaluate selected submissions"
reevaluate_submissions.allowed_permissions = ("change",)


class SubmissionAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = ("pk", "created", "phase", "creator")
    list_filter = ("phase__challenge__short_name",)
    search_fields = ("pk", "creator__username", "phase__slug")
    readonly_fields = (
        "creator",
        "phase",
        "predictions_file",
        "algorithm_image",
    )
    actions = (reevaluate_submissions,)


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
        "attempt",
        "stdout",
        "stderr",
        "error_message",
        "input_prefixes",
        "task_on_success",
        "task_on_failure",
        "runtime_metrics",
    )
    actions = (requeue_jobs, cancel_jobs, deprovision_jobs)


admin.site.register(Phase, PhaseAdmin)
admin.site.register(Method, ComponentImageAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(Evaluation, EvaluationAdmin)
