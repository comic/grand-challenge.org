from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.forms import ModelForm

from grandchallenge.challenges.models import ChallengeRequest
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
from grandchallenge.evaluation.models import (
    Evaluation,
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
from grandchallenge.evaluation.utils import SubmissionKindChoices


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

        submission_kind = cleaned_data["submission_kind"]
        total_number_of_submissions_allowed = cleaned_data[
            "total_number_of_submissions_allowed"
        ]

        if (
            submission_kind == SubmissionKindChoices.ALGORITHM
            and not total_number_of_submissions_allowed
        ):
            try:
                request = ChallengeRequest.objects.get(
                    short_name=self.instance.challenge.short_name
                )
                error_addition = f"The corresponding challenge request lists the following limits: Preliminary phase: {request.phase_1_number_of_submissions_per_team * request.expected_number_of_teams} Final test phase: {request.phase_2_number_of_submissions_per_team * request.expected_number_of_teams}. Set the limits according to the phase type. "
            except ObjectDoesNotExist:
                error_addition = "There is no corresponding challenge request."
            raise ValidationError(
                "For phases that take an algorithm as submission input, "
                "the total_number_of_submissions_allowed needs to be set. "
                + error_addition
            )

        return cleaned_data


@admin.register(Phase)
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
        "submissions_limit_per_user_per_period",
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


@admin.register(Evaluation)
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
