from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.core.exceptions import ValidationError

from grandchallenge.challenges.emails import send_challenge_status_update_email
from grandchallenge.challenges.models import (
    Challenge,
    ChallengeRequest,
    ChallengeSeries,
    ExternalChallenge,
)


class ChallengeAdmin(ModelAdmin):
    readonly_fields = ("creator",)
    autocomplete_fields = ("publications",)
    ordering = ("-created",)
    list_display = ("short_name", "created")
    search_fields = ("short_name",)


class ExternalChallengeAdmin(ModelAdmin):
    readonly_fields = ("creator",)
    autocomplete_fields = ("publications",)


class ChallengeRequestAdmin(ModelAdmin):
    readonly_fields = ("creator",)
    ordering = ("-created",)
    list_display = (
        "title",
        "short_name",
        "creator",
        "created",
        "status",
        "challenge_type",
        "total_cost",
        "budget_for_hosting_challenge",
    )
    actions = ["create_challenge", "send_status_update_email"]
    list_filter = ["status", "challenge_type"]

    @admin.display(description="Total cost")
    def total_cost(self, obj):
        if obj.budget:
            return obj.budget.get("Total")
        else:
            return None

    @admin.action(description="Create challenge for this request")
    def create_challenge(self, request, queryset):
        for challengerequest in queryset:
            try:
                challengerequest.create_challenge()
            except ValidationError:
                self.message_user(
                    request,
                    f"There already is a challenge with short "
                    f"name: {challengerequest.short_name}",
                    messages.WARNING,
                )

    @admin.action(description="Send status update email to requester")
    def send_status_update_email(self, request, queryset):
        for challengerequest in queryset:
            if (
                challengerequest.status
                == challengerequest.ChallengeRequestStatusChoices.ACCEPTED
            ):
                try:
                    challenge = Challenge.objects.get(
                        short_name=challengerequest.short_name
                    )
                except Challenge.DoesNotExist:
                    challenge = challengerequest.create_challenge()
            else:
                challenge = None
            send_challenge_status_update_email(
                challengerequest=challengerequest, challenge=challenge
            )


admin.site.register(Challenge, ChallengeAdmin)
admin.site.register(ExternalChallenge, ExternalChallengeAdmin)
admin.site.register(ChallengeSeries)
admin.site.register(ChallengeRequest, ChallengeRequestAdmin)
