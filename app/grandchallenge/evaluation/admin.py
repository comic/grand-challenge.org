import json

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils.html import format_html

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
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.core.utils.grand_challenge_forge import (
    get_forge_challenge_pack_context,
)
from grandchallenge.evaluation.models import (
    CombinedLeaderboard,
    Evaluation,
    EvaluationGroundTruth,
    EvaluationGroupObjectPermission,
    EvaluationUserObjectPermission,
    Method,
    MethodGroupObjectPermission,
    MethodUserObjectPermission,
    Phase,
    PhaseGroupObjectPermission,
    PhaseUserObjectPermission,
    Submission,
    SubmissionGroupObjectPermission,
    SubmissionUserObjectPermission,
)
from grandchallenge.evaluation.tasks import create_evaluation


class PhaseAdminForm(ModelForm):
    class Meta:
        model = Phase
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = self.instance.parent_phase_choices
        if self.instance.parent or self.instance.children.exists():
            for (
                field_name
            ) in self.instance.read_only_fields_for_dependent_phases:
                self.fields[field_name].disabled = True

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


@admin.register(Phase)
class PhaseAdmin(admin.ModelAdmin):
    ordering = ("challenge",)
    list_display = (
        "slug",
        "title",
        "challenge",
        "parent",
        "submission_kind",
        "submissions_open_at",
        "submissions_close_at",
        "submissions_limit_per_user_per_period",
        "give_algorithm_editors_job_view_permissions",
        "external_evaluation",
    )
    search_fields = ("pk", "title", "slug", "challenge__short_name")
    list_filter = (
        "submission_kind",
        "give_algorithm_editors_job_view_permissions",
        "challenge__short_name",
        "external_evaluation",
    )
    autocomplete_fields = (
        "inputs",
        "outputs",
        "algorithm_inputs",
        "algorithm_outputs",
        "archive",
    )
    readonly_fields = (
        "give_algorithm_editors_job_view_permissions",
        "challenge_forge_json",
    )
    form = PhaseAdminForm

    @admin.display(boolean=True)
    def open_for_submissions(self, instance):
        return instance.open_for_submissions

    @staticmethod
    def challenge_forge_json(obj):
        json_desc = get_forge_challenge_pack_context(
            challenge=obj.challenge,
            phase_pks=[obj.pk],
        )
        return format_html(
            "<pre>{json_desc}</pre>", json_desc=json.dumps(json_desc, indent=2)
        )


@admin.action(
    description="Reevaluate selected submissions",
    permissions=("change",),
)
def reevaluate_submissions(modeladmin, request, queryset):
    """Creates a new evaluation for an existing submission"""
    for submission in queryset:
        create_evaluation.apply_async(
            kwargs={"submission_pk": str(submission.pk)}
        )


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = (
        "pk",
        "created",
        "phase",
        "creator",
        "algorithm_image",
        "algorithm_requires_gpu_type",
        "algorithm_requires_memory_gb",
    )
    list_filter = ("phase__submission_kind", "phase__challenge__short_name")
    search_fields = ("pk", "creator__username", "phase__slug")
    readonly_fields = (
        "creator",
        "phase",
        "predictions_file",
        "algorithm_image",
    )
    actions = (reevaluate_submissions,)


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = (
        "pk",
        "created",
        "submission",
        "compute_cost_euro_millicents",
        "time_limit",
        "requires_gpu_type",
        "requires_memory_gb",
        "status",
        "published",
        "error_message",
    )
    list_filter = (
        "status",
        "published",
        "requires_gpu_type",
        "submission__phase__submission_kind",
        "submission__phase__challenge__short_name",
    )
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
        "claimed_by",
        "ground_truth",
    )
    actions = (requeue_jobs, cancel_jobs, deprovision_jobs)


@admin.register(CombinedLeaderboard)
class CombinedLeaderboardAdmin(admin.ModelAdmin):
    readonly_fields = (
        "challenge",
        "phases",
    )


@admin.register(EvaluationGroundTruth)
class EvaluationGroundTruthAdmin(admin.ModelAdmin):
    exclude = ("ground_truth",)
    list_display = ("phase", "created", "is_desired_version", "comment")
    list_filter = ("is_desired_version",)
    search_fields = ("phase__slug", "comment")
    readonly_fields = ("creator", "phase", "sha256", "size_in_storage")


admin.site.register(PhaseUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(PhaseGroupObjectPermission, GroupObjectPermissionAdmin)
admin.site.register(Method, ComponentImageAdmin)
admin.site.register(MethodUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(MethodGroupObjectPermission, GroupObjectPermissionAdmin)
admin.site.register(SubmissionUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(
    SubmissionGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(EvaluationUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(
    EvaluationGroupObjectPermission, GroupObjectPermissionAdmin
)
