from django.contrib import admin
from django.utils.timezone import now

from grandchallenge.verifications.models import Verification


def mark_verified(modeladmin, request, queryset):
    queryset.update(is_verified=True, verified_at=now())


mark_verified.short_description = "Mark selected users as verified"
mark_verified.allowed_permissions = ("change",)


def mark_not_verified(modeladmin, request, queryset):
    queryset.update(is_verified=False, verified_at=None)


mark_not_verified.short_description = "Mark selected users as not verified"
mark_not_verified.allowed_permissions = ("change",)


class VerificationAdmin(admin.ModelAdmin):
    list_select_related = ("user__userena_signup",)
    list_display = (
        "user",
        "created",
        "signup_email",
        "signup_email_activated",
        "email",
        "email_is_verified",
        "is_verified",
        "verified_at",
    )
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

    def signup_email_activated(self, instance):
        return instance.signup_email_activated

    signup_email_activated.boolean = True

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("user", "email", *self.readonly_fields)
        else:
            return self.readonly_fields


admin.site.register(Verification, VerificationAdmin)
