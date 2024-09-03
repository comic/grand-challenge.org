from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from grandchallenge.participants.models import RegistrationQuestion


@admin.register(RegistrationQuestion)
class RegistrationQuestion(GuardedModelAdmin):
    list_display = (
        "pk",
        "question_text",
        "challenge",
    )
    ordering = ("challenge",)
    readonly_fields = ("question_text", "question_help_text", "required")

    list_filter = ("challenge__short_name",)
