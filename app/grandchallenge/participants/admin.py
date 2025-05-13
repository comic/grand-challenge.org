from django.contrib import admin

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.participants.models import (
    RegistrationQuestion,
    RegistrationQuestionAnswer,
    RegistrationQuestionGroupObjectPermission,
    RegistrationQuestionUserObjectPermission,
    RegistrationRequest,
)


@admin.register(RegistrationRequest)
class RegistrationRequestAdmin(admin.ModelAdmin):
    readonly_fields = ("user", "challenge")


@admin.register(RegistrationQuestion)
class RegistrationQuestionAdmin(admin.ModelAdmin):
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


@admin.register(RegistrationQuestionAnswer)
class RegistrationQuestionAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "registration_request",
        "user",
        "question_text",
        "answer",
    )
    search_fields = ("registration_request__user__username",)
    ordering = ("registration_request__challenge",)
    readonly_fields = ("registration_request", "question")
    list_select_related = (
        "registration_request__challenge",
        "registration_request__user",
        "question",
    )
    list_filter = ("registration_request__challenge__short_name",)

    def user(self, instance):
        return instance.registration_request.user

    def question_text(self, instance):
        return instance.question.question_text
