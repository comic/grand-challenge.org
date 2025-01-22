import json
from datetime import timedelta

from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.core.exceptions import ValidationError
from django.db.models import BooleanField, Case, F, Value, When
from django.utils.html import format_html
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from grandchallenge.challenges.emails import send_challenge_status_update_email
from grandchallenge.challenges.models import (
    Challenge,
    ChallengeGroupObjectPermission,
    ChallengeRequest,
    ChallengeRequestGroupObjectPermission,
    ChallengeRequestUserObjectPermission,
    ChallengeSeries,
    ChallengeUserObjectPermission,
    OnboardingTask,
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


class OnTimeFilter(admin.SimpleListFilter):
    title = _("on time")
    parameter_name = "on_time"

    def lookups(self, *_, **__):
        return [
            (True, "Yes"),
            (False, "No"),
        ]

    def queryset(self, request, queryset):
        if self.value() is not None:
            queryset = queryset.filter(overdue=not self.value())
        return queryset


@admin.action(
    description="Mark selected onboarding tasks complete",
    permissions=("change",),
)
def mark_complete(modeladmin, request, queryset):
    queryset.update(complete=True)


@admin.action(
    description="Move selected task' deadlines by 1 week",
    permissions=("change",),
)
def move_deadline_1_week(modeladmin, request, queryset):
    queryset.update(deadline=F("deadline") + timedelta(weeks=1))


@admin.action(
    description="Move selected task' deadlines by 4 weeks",
    permissions=("change",),
)
def move_deadline_4_weeks(modeladmin, request, queryset):
    queryset.update(deadline=F("deadline") + timedelta(weeks=4))


@admin.register(OnboardingTask)
class OnboardingTaskAdmin(ModelAdmin):
    ordering = (
        "challenge",
        "-deadline",
    )
    autocomplete_fields = ("challenge",)
    list_display = (
        "title",
        "challenge",
        "on_time",
        "complete",
        "deadline",
        "responsible",
    )
    list_filter = (
        OnTimeFilter,
        "complete",
        "challenge__short_name",
    )
    list_select_related = ("challenge",)
    search_fields = ("title", "description")
    actions = (
        mark_complete,
        move_deadline_1_week,
        move_deadline_4_weeks,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reference_time = now()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            overdue=Case(
                When(complete=False, deadline__lt=now(), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )

    @admin.display(boolean=True)
    def on_time(self, obj):
        return not obj.overdue


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
