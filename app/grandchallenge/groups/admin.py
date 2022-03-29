from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group


class UserInLine(admin.TabularInline):
    model = get_user_model().groups.through
    raw_id_fields = ("user",)


class GroupWithUsers(GroupAdmin):
    inlines = [UserInLine]


admin.site.unregister(Group)
admin.site.register(Group, GroupWithUsers)
