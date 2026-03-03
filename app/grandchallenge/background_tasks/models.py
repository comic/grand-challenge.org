from django.db import models


class CeleryTaskDailyStats(models.Model):
    date = models.DateField()
    task_name = models.CharField(max_length=255)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)
    avg_duration = models.DurationField(
        null=True, help_text="Average duration of successful jobs on date"
    )
    min_duration = models.DurationField(
        null=True, help_text="Minimum duration of successful jobs on date"
    )
    max_duration = models.DurationField(
        null=True, help_text="Maximum duration of successful jobs on date"
    )

    class Meta:
        unique_together = [("date", "task_name")]
