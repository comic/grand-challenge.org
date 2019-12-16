from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group
from rest_framework.authtoken.models import Token

admin.site.unregister(Group)
admin.site.unregister(Token)


class ReadOnlyUserInLine(admin.TabularInline):
    model = get_user_model().groups.through
    extra = 0
    can_delete = False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Group)
class GroupWithUsers(GroupAdmin):
    inlines = [ReadOnlyUserInLine]


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ("key", "user", "created")
    fields = ("user",)
    ordering = ("-created",)
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
