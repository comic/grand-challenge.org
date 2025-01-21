import json

from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from grandchallenge.challenges.emails import send_challenge_status_update_email
from grandchallenge.challenges.models import (
    Challenge,
    ChallengeGroupObjectPermission,
    ChallengeRequest,
    ChallengeRequestGroupObjectPermission,
    ChallengeRequestUserObjectPermission,
    ChallengeSeries,
    ChallengeUserObjectPermission,
    OnboardingTaskGroupObjectPermission,
)
from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.core.templatetags.costs import millicents_to_euro
from grandchallenge.core.utils.grand_challenge_forge import (
    get_forge_challenge_pack_context,
)
from grandchallenge.subdomains.utils import reverse


@admin.register(Challenge)
class ChallengeAdmin(ModelAdmin):
    readonly_fields = (
        "short_name",
        "creator",
        "challenge_forge_json",
        "algorithm_phase_configuration_link",
    )
    autocomplete_fields = ("publications",)
    ordering = ("-created",)
    list_display = (
        "short_name",
        "created",
        "hidden",
        "is_suspended",
        "is_active_until",
        "compute_cost_euro_millicents",
        "size_in_storage",
        "size_in_registry",
        "available_compute_euros",
    )
    list_filter = (
        "is_suspended",
        "hidden",
    )
    search_fields = ("short_name",)

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).with_available_compute()

    def available_compute_euros(self, obj):
        return millicents_to_euro(obj.available_compute_euro_millicents)

    @staticmethod
    def challenge_forge_json(obj):
        json_desc = get_forge_challenge_pack_context(challenge=obj)
        return format_html(
            "<pre>{json_desc}</pre>", json_desc=json.dumps(json_desc, indent=2)
        )

    @staticmethod
    def algorithm_phase_configuration_link(obj):
        return format_html(
            '<a href="{link}">{link}</a>',
            link=reverse(
                "evaluation:configure-algorithm-phases",
                kwargs={"challenge_short_name": obj.short_name},
            ),
        )


@admin.register(ChallengeRequest)
class ChallengeRequestAdmin(ModelAdmin):
    readonly_fields = ("creator",)
    ordering = ("-created",)
    list_display = (
        "title",
        "short_name",
        "creator",
        "created",
        "status",
        "total_cost",
    )
    actions = ["create_challenge", "send_status_update_email"]
    list_filter = ["status"]

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


admin.site.register(ChallengeUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(ChallengeGroupObjectPermission, GroupObjectPermissionAdmin)
admin.site.register(
    ChallengeRequestUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    ChallengeRequestGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(ChallengeSeries)

admin.site.register(
    OnboardingTaskGroupObjectPermission, GroupObjectPermissionAdmin
)
