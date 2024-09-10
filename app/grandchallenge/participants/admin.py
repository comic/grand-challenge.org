from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.participants.models import (
    RegistrationQuestion,
    RegistrationQuestionGroupObjectPermission,
    RegistrationQuestionUserObjectPermission,
)


@admin.register(RegistrationQuestion)
class RegistrationQuestionAdmin(GuardedModelAdmin):
    list_display = (
        "pk",
        "question_text",
        "challenge",
    )
    ordering = ("challenge",)
    readonly_fields = ("challenge",)

    list_filter = ("challenge__short_name",)


admin.site.register(
    RegistrationQuestionUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    RegistrationQuestionGroupObjectPermission, GroupObjectPermissionAdmin
)
