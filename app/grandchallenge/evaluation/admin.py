from django.contrib import admin, messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.forms import Form, ModelForm, ModelMultipleChoiceField
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.text import slugify
from django.views.generic import FormView

from grandchallenge.archives.models import Archive
from grandchallenge.components.admin import (
    ComponentImageAdmin,
    cancel_jobs,
    deprovision_jobs,
    requeue_jobs,
)
from grandchallenge.components.models import ComponentInterface
from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.evaluation.models import (
    CombinedLeaderboard,
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

        return cleaned_data


class ConfigureAlgorithmPhasesForm(Form):
    phases = ModelMultipleChoiceField(
        queryset=Phase.objects.select_related("challenge")
        .filter(submission_kind=SubmissionKindChoices.CSV)
        .all()
    )
    algorithm_inputs = ModelMultipleChoiceField(
        queryset=ComponentInterface.objects.all()
    )
    algorithm_outputs = ModelMultipleChoiceField(
        queryset=ComponentInterface.objects.all()
    )

    def clean(self):
        cleaned_data = super().clean()
        try:
            for phase in self.cleaned_data["phases"]:
                if Archive.objects.filter(
                    slug=f"{slugify(phase.challenge.short_name)}-{slugify(phase.title)}-dataset"
                ).exists():
                    raise ValidationError(
                        f"Archive for {phase} already exists."
                    )
        except KeyError:
            pass
        return cleaned_data


class ConfigureAlgorithmPhasesView(PermissionRequiredMixin, FormView):
    form_class = ConfigureAlgorithmPhasesForm
    permission_required = "evaluation.configure_algorithm_phase"
    template_name = "admin/evaluation/phase/algorithm_phase_form.html"
    raise_exception = True

    def form_valid(self, form):
        for phase in form.cleaned_data["phases"]:
            self.turn_phase_into_algorithm_phase(
                phase=phase,
                inputs=form.cleaned_data["algorithm_inputs"],
                outputs=form.cleaned_data["algorithm_outputs"],
            )
        messages.success(self.request, "Phases were successfully updated")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                **admin.site.each_context(self.request),
                "opts": Phase._meta,
                "title": "Turn phase(s) into algorithm phase(s)",
            }
        )
        return context

    def get_success_url(self):
        return reverse("admin:evaluation_phase_changelist")

    def turn_phase_into_algorithm_phase(self, *, phase, inputs, outputs):
        archive = Archive.objects.create(
            title=format_html(
                "{challenge_name} {phase_title} dataset",
                challenge_name=phase.challenge.short_name,
                phase_title=phase.title,
            )
        )

        for user in phase.challenge.admins_group.user_set.all():
            archive.add_editor(user)

        phase.archive = archive
        phase.submission_kind = phase.SubmissionKindChoices.ALGORITHM
        phase.creator_must_be_verified = True
        phase.save()
        phase.algorithm_outputs.add(*outputs)
        phase.algorithm_inputs.add(*inputs)


@admin.register(Phase)
class PhaseAdmin(admin.ModelAdmin):
    ordering = ("challenge",)
    list_display = (
        "slug",
        "title",
        "challenge",
        "submission_kind",
        "submissions_open_at",
        "submissions_close_at",
        "submissions_limit_per_user_per_period",
        "give_algorithm_editors_job_view_permissions",
    )
    search_fields = ("pk", "title", "slug", "challenge__short_name")
    list_filter = (
        "submission_kind",
        "challenge__short_name",
        "give_algorithm_editors_job_view_permissions",
    )
    autocomplete_fields = (
        "inputs",
        "outputs",
        "algorithm_inputs",
        "algorithm_outputs",
        "archive",
    )
    readonly_fields = ("give_algorithm_editors_job_view_permissions",)
    form = PhaseAdminForm
    change_list_template = "admin/evaluation/phase/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        extra_url = [
            path(
                "create_algorithm_phase/",
                self.admin_site.admin_view(
                    ConfigureAlgorithmPhasesView.as_view()
                ),
                name="algorithm_phase_create",
            )
        ]
        return extra_url + urls

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


@admin.register(CombinedLeaderboard)
class CombinedLeaderboardAdmin(admin.ModelAdmin):
    readonly_fields = (
        "challenge",
        "phases",
    )


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
