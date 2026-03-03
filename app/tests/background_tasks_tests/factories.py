import factory
from celery import states
from django_celery_results.models import TaskResult


class TaskResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TaskResult

    task_id = factory.Sequence(lambda n: f"task-{n}")
    task_name = "myapp.tasks.foo"
    status = states.SUCCESS
    content_type = "application/json"
    content_encoding = "utf-8"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        date_started = kwargs.pop("date_started", None)
        date_done = kwargs.pop("date_done", None)

        instance = super()._create(model_class, *args, **kwargs)

        if date_started or date_done:
            update_fields = {}
            if date_started:
                update_fields["date_started"] = date_started
            if date_done:
                update_fields["date_done"] = date_done
            TaskResult.objects.filter(pk=instance.pk).update(**update_fields)
            instance.refresh_from_db()

        return instance
