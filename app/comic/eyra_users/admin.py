from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as OriginalUserAdmin
from django.contrib.auth.models import User, Group

from guardian.admin import GuardedModelAdmin


class UserAdmin(OriginalUserAdmin, GuardedModelAdmin):
    pass


class UserInLine(admin.TabularInline):
    model = Group.user_set.through
    extra = 0


class GroupAdmin(GuardedModelAdmin):
    list_display = ('name',)
    list_filter = ()
    inlines = [UserInLine]
    filter_horizontal = ('permissions',)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)