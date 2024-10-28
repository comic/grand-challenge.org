from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.transaction import on_commit
from django.template.defaultfilters import linebreaksbr
from django.utils.timezone import now
from pyswot import find_school_names, is_academic

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
    verifications = queryset.filter(email_is_verified=True)

    for verification in verifications:
        verification.is_verified = True
        verification.verified_at = now()
        verification.save()


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
        "email_school_names",
        "signup_email_if_different",
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

    def email_school_names(self, obj):
        return linebreaksbr("\n".join(find_school_names(obj.email)))

    def user_sets(self, obj):
        usernames = set()
        comments = []

        for vus in obj.user.verificationuserset_set.all():
            if vus.is_false_positive:
                comments.append("False Positive VUS.")

            if vus.comment:
                comments.append(vus.comment)

            for user in vus.users.all():
                if user != obj.user:
                    usernames.add(user.username)

        out_usernames = ", ".join(usernames)
        out_comments = "\n".join(comments)

        return linebreaksbr(f"{out_usernames}\n\n{out_comments}")

    def user_info(self, instance):
        return instance.user.user_profile.user_info

    @admin.display(boolean=True)
    def email_is_academic(self, instance):
        return is_academic(email=instance.email)

    def signup_email_if_different(self, instance):
        signup_email = instance.user.email

        if signup_email == instance.email:
            return ""
        else:
            signup_email_school_names = "\n".join(
                find_school_names(signup_email)
            )
            return linebreaksbr(
                f"{signup_email}\n\n{signup_email_school_names}"
            )

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
        .objects.filter(verificationuserset__in=queryset, is_active=True)
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
        "modified",
        "auto_deactivate",
        "is_false_positive",
        "active_usernames",
        "inactive_usernames",
        "comment",
    )
    search_fields = ("users__username",)
    actions = (deactivate_vus_users,)
    list_filter = (
        "auto_deactivate",
        "is_false_positive",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("users")

    def active_usernames(self, obj):
        return ", ".join(
            user.username for user in obj.users.all() if user.is_active
        )

    def inactive_usernames(self, obj):
        return ", ".join(
            user.username for user in obj.users.all() if not user.is_active
        )
