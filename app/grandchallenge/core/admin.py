from celery import states
from django.contrib import admin
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.forms import FlatpageForm
from django.contrib.flatpages.models import FlatPage
from django_celery_results.admin import TaskResultAdmin
from django_celery_results.models import TaskResult

from grandchallenge.core.widgets import MarkdownEditorAdminWidget


class MarkdownFlatPageForm(FlatpageForm):
    class Meta(FlatpageForm.Meta):
        widgets = {"content": MarkdownEditorAdminWidget()}


class MarkdownFlatPageAdmin(FlatPageAdmin):
    form = MarkdownFlatPageForm


class UserObjectPermissionAdmin(admin.ModelAdmin):
    readonly_fields = ("user", "permission", "content_object")
    search_fields = ("user__username", "content_object__pk")
    list_display = ("user", "permission", "content_object")


class GroupObjectPermissionAdmin(admin.ModelAdmin):
    readonly_fields = ("group", "permission", "content_object")
    search_fields = ("group__name", "content_object__pk")
    list_display = ("group", "permission", "content_object")


admin.site.unregister(FlatPage)
admin.site.register(FlatPage, MarkdownFlatPageAdmin)


class TaskResultAdminWithDuration(TaskResultAdmin):
    list_display = (
        "task_id",
        "periodic_task_name",
        "task_name",
        "date_done",
        "get_duration",
        "status",
        "worker",
    )

    @admin.display(description="Duration")
    def get_duration(self, obj):
        if obj.status in {states.SUCCESS, states.FAILURE}:
            return obj.date_done - obj.date_started
        else:
            return None


admin.site.unregister(TaskResult)
admin.site.register(TaskResult, TaskResultAdminWithDuration)
