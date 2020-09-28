from django.contrib import admin

from grandchallenge.verifications.models import Verification


class VerificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "created",
        "email",
        "email_is_verified",
        "is_verified",
        "verified_at",
    )
    list_filter = (
        "email_is_verified",
        "is_verified",
    )
    readonly_fields = (
        "created",
        "modified",
        "email_is_verified",
        "email_verified_at",
        "is_verified",
        "verified_at",
    )
    search_fields = (
        "user__username",
        "email",
        "user__email",
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("user", "email", *self.readonly_fields)
        else:
            return self.readonly_fields


admin.site.register(Verification, VerificationAdmin)
