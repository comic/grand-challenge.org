from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from grandchallenge.profiles.models import UserProfile
from grandchallenge.profiles.tasks import deactivate_user


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    max_num = 1
    can_delete = False


def deactivate_users(modeladmin, request, queryset):
    for user in queryset:
        deactivate_user.signature(kwargs={"user_pk": user.pk}).apply_async()


deactivate_users.short_description = "Deactivate users"
deactivate_users.allowed_permissions = ("change",)


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
    )
    list_filter = ("is_staff", "is_superuser", "is_active")
    actions = (deactivate_users,)


User = get_user_model()
admin.site.unregister(User)
admin.site.register(User, UserProfileAdmin)
