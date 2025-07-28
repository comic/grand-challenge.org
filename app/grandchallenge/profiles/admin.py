from allauth.mfa.utils import is_mfa_enabled
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.profiles.models import (
    BannedEmailAddress,
    UserProfile,
    UserProfileGroupObjectPermission,
    UserProfileUserObjectPermission,
)
from grandchallenge.profiles.tasks import deactivate_user


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    max_num = 1
    can_delete = False


@admin.action(
    description="Deactivate users",
    permissions=("change",),
)
def deactivate_users(modeladmin, request, queryset):
    for user in queryset.filter(is_active=True):
        deactivate_user.signature(kwargs={"user_pk": user.pk}).apply_async()


class UserProfileAdmin(UserAdmin):
    inlines = [UserProfileInline]
    autocomplete_fields = ("groups",)
    readonly_fields = ("user_permissions",)
    list_display = (
        "username",
        "date_joined",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "has_2fa_enabled",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "user_profile__receive_newsletter",
        "user_profile__notification_email_choice",
        "user_profile__country",
    )
    actions = (deactivate_users,)

    @admin.display(boolean=True, description="User has 2FA enabled")
    def has_2fa_enabled(self, obj):
        return is_mfa_enabled(obj)


@admin.register(BannedEmailAddress)
class BannedEmailAddressAdmin(admin.ModelAdmin):
    list_display = ("pk", "created", "email", "reason")
    search_fields = ("email",)


User = get_user_model()
admin.site.unregister(User)
admin.site.register(User, UserProfileAdmin)
admin.site.register(UserProfileUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(
    UserProfileGroupObjectPermission, GroupObjectPermissionAdmin
)
