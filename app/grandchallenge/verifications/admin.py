from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.transaction import on_commit
from django.utils.timezone import now
from pyswot import is_academic

from grandchallenge.profiles.tasks import deactivate_user
from grandchallenge.verifications.models import (
    Verification,
    VerificationUserSet,
)


@admin.action(
    description="Mark selected users as verified",
    permissions=("change",),
)
def mark_verified(modeladmin, request, queryset):
    queryset.filter(email_is_verified=True).update(
        is_verified=True, verified_at=now()
    )


@admin.action(
    description="Mark selected users as not verified",
    permissions=("change",),
)
def mark_not_verified(modeladmin, request, queryset):
    queryset.update(is_verified=False, verified_at=None)


@admin.action(
    description="Resend confirmation email",
    permissions=("change",),
)
def resend_confirmation_email(modeladmin, request, queryset):
    for verification in queryset.filter(email_is_verified=False).exclude(
        is_verified=True
    ):
        verification.send_verification_email()


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "user_sets",
        "user_info",
        "created",
        "signup_email",
        "email",
        "email_is_academic",
        "email_is_verified",
        "is_verified",
        "verified_at",
    )
    list_select_related = ("user__user_profile",)
    list_filter = ("email_is_verified", "is_verified")
    readonly_fields = (
        "created",
        "modified",
        "email_is_verified",
        "email_verified_at",
        "is_verified",
        "verified_at",
    )
    search_fields = ("user__username", "email", "user__email")
    actions = (mark_verified, mark_not_verified, resend_confirmation_email)
    autocomplete_fields = ("user",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related(
            "user__verificationuserset_set__users"
        )
        return queryset

    def user_sets(self, obj):
        usernames = set()

        for vus in obj.user.verificationuserset_set.all():
            for user in vus.users.all():
                if user != obj.user:
                    usernames.add(user.username)

        return ", ".join(usernames)

    def user_info(self, instance):
        return instance.user.user_profile.user_info

    @admin.display(boolean=True)
    def email_is_academic(self, instance):
        return is_academic(email=instance.email)

    def signup_email(self, instance):
        return instance.user.email

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("user", "email", *self.readonly_fields)
        else:
            return self.readonly_fields


@admin.action(
    description="Deactivate users",
    permissions=("change",),
)
def deactivate_vus_users(modeladmin, request, queryset):
    users = (
        get_user_model()
        .objects.filter(verificationuserset__in=queryset)
        .distinct()
    )

    for user in users:
        on_commit(
            deactivate_user.signature(kwargs={"user_pk": user.pk}).apply_async
        )


@admin.register(VerificationUserSet)
class VerificationUserSetAdmin(admin.ModelAdmin):
    readonly_fields = ("users",)
    list_display = (
        "pk",
        "created",
        "active_usernames",
        "inactive_usernames",
    )
    list_prefetch_related = ("users",)
    search_fields = ("users__username",)
    actions = (deactivate_vus_users,)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset.prefetch_related("users")
        return queryset

    def active_usernames(self, obj):
        return ", ".join(
            user.username for user in obj.users.all() if user.is_active
        )

    def inactive_usernames(self, obj):
        return ", ".join(
            user.username for user in obj.users.all() if not user.is_active
        )
