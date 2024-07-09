from functools import wraps

from celery import shared_task  # noqa: I251 Usage allowed here
from django.conf import settings


class AcksLateTaskDecorator:
    def __init__(self, queue):
        if queue not in settings.CELERY_SOLO_QUEUES:
            raise ValueError(f"Queue {queue} is not a solo queue")

        if f"{queue}-delay" not in settings.CELERY_SOLO_QUEUES:
            raise ValueError(f"Queue {queue}-delay is not a solo queue")

        self.queue = queue

    def __call__(self, func=None, ignore_result=False, throws=()):
        if func is None:
            # Called as @decorator(**extra_kwargs)
            return lambda func: self._decorator(
                func=func, ignore_result=ignore_result, throws=throws
            )
        else:
            # Called as @decorator or @decorator(func)
            return self._decorator(
                func=func, ignore_result=ignore_result, throws=throws
            )

    def _decorator(self, *, func, ignore_result, throws):

        @shared_task(
            acks_late=True,
            reject_on_worker_lost=True,
            queue=self.queue,
            ignore_result=ignore_result,
            throws=throws,
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper


# For idempotent tasks that take a long time (<7200s)
# or require a large amount of memory
acks_late_2xlarge_task = AcksLateTaskDecorator("acks-late-2xlarge")

# For idempotent tasks that take a short time (<300s)
# and do not require a large amount of memory
acks_late_micro_short_task = AcksLateTaskDecorator("acks-late-micro-short")
