from django.contrib import admin

from grandchallenge.background_tasks.models import CeleryTaskDailyStats


@admin.register(CeleryTaskDailyStats)
class CeleryTaskDailyStatsAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "task_name",
        "success_count",
        "failure_count",
        "avg_duration",
        "min_duration",
        "max_duration",
    ]
    list_filter = ["date", "task_name"]
    search_fields = ["task_name"]
    ordering = ["-date", "task_name"]
    date_hierarchy = "date"

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("-date", "task_name")
