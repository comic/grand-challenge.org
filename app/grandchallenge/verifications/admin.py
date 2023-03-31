from django.contrib import admin
from django.utils.timezone import now
from pyswot import is_academic

from grandchallenge.verifications.models import Verification


@admin.action(
    description="Mark selected users as verified",
    permissions=("change",),
)
def mark_verified(modeladmin, request, queryset):
    queryset.update(is_verified=True, verified_at=now())


@admin.action(
    description="Mark selected users as not verified",
    permissions=("change",),
)
def mark_not_verified(modeladmin, request, queryset):
    queryset.update(is_verified=False, verified_at=None)


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "user_info",
        "created",
        "signup_email",
        "signup_email_is_academic",
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
    actions = (mark_verified, mark_not_verified)
    autocomplete_fields = ("user",)

    @admin.display(boolean=True)
    def email_is_academic(self, instance):
        return is_academic(email=instance.email)

    @admin.display(boolean=True)
    def signup_email_is_academic(self, instance):
        return is_academic(email=instance.signup_email)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("user", "email", *self.readonly_fields)
        else:
            return self.readonly_fields
