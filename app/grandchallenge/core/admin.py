from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.forms import FlatpageForm
from django.contrib.flatpages.models import FlatPage

from grandchallenge.core.widgets import MarkdownEditorAdminWidget


class ReadOnlyUserInLine(admin.TabularInline):
    model = get_user_model().groups.through
    extra = 0
    can_delete = False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


class GroupWithUsers(GroupAdmin):
    inlines = [ReadOnlyUserInLine]


class MarkdownFlatPageForm(FlatpageForm):
    class Meta(FlatpageForm.Meta):
        widgets = {
            "content": MarkdownEditorAdminWidget(),
        }


class MarkdownFlatPageAdmin(FlatPageAdmin):
    form = MarkdownFlatPageForm


admin.site.unregister(Group)
admin.site.register(Group, GroupWithUsers)

admin.site.unregister(FlatPage)
admin.site.register(FlatPage, MarkdownFlatPageAdmin)
