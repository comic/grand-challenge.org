from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group

admin.site.unregister(Group)


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
