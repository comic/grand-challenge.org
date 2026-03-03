from datetime import timedelta

import factory
from django.utils import timezone
from django_celery_results.models import TaskResult


class TaskResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TaskResult

    task_id = factory.Sequence(lambda n: f"task-{n}")
    task_name = "myapp.tasks.foo"
    status = "SUCCESS"
    content_type = "application/json"
    content_encoding = "utf-8"
    date_started = factory.LazyFunction(
        lambda: timezone.now() - timedelta(days=1, seconds=10)
    )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        date_started = kwargs.get("date_started")
        date_done = kwargs.pop(
            "date_done",
            (
                (date_started + timedelta(seconds=10))
                if date_started
                else timezone.now() - timedelta(days=1)
            ),
        )
        instance = super()._create(model_class, *args, **kwargs)
        TaskResult.objects.filter(pk=instance.pk).update(date_done=date_done)
        instance.refresh_from_db()
        return instance
