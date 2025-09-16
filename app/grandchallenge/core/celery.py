import logging
import random
import time
from functools import wraps

from celery import shared_task  # noqa: I251 Usage allowed here
from celery.exceptions import MaxRetriesExceededError
from django.conf import settings
from django.core.cache import cache
from django.db.transaction import on_commit
from redis.exceptions import LockError

logger = logging.getLogger(__name__)

MAX_RETRIES = 60 * 24 * 2  # 2 days assuming 1 minute delay


def _retry(*, task, signature_kwargs, retries, delayed=True):
    """
    Retry a task using the delay queue

    We need to retry a task with a delay/countdown. There are several problems
    with doing this in Celery (with SQS/Redis).

    - If a countdown is used the delay features of SQS are not used
      https://github.com/celery/kombu/issues/1074
    - A countdown that needs to be done on the worker results backlogs
      https://github.com/celery/celery/issues/2541
    - The backlogs can still occur even if the countdown/eta is set to zero
      https://github.com/celery/celery/issues/6929

    This method is a workaround for these issues, that creates a new task
    and places this on a queue which has DelaySeconds set. The downside
    is that we need to track retries via the kwargs of the task.
    """
    if retries < MAX_RETRIES:
        step = task.signature(**signature_kwargs)
        step.kwargs["_retries"] = retries + 1

        if delayed:
            queue = step.options.get("queue", task.queue)
            step.options["queue"] = f"{queue}-delay"
        else:
            # Add some jitter
            time.sleep(random.uniform(0, 5))

        on_commit(step.apply_async)
    else:
        raise MaxRetriesExceededError


def _cache_key_from_method(method):
    return f"lock.{method.__module__}.{method.__name__}"


class AcksLateTaskDecorator:
    def __init__(self, queue):
        if queue not in settings.CELERY_SOLO_QUEUES:
            raise ValueError(f"Queue {queue} is not a solo queue")

        if f"{queue}-delay" not in settings.CELERY_SOLO_QUEUES:
            raise ValueError(f"Queue {queue}-delay is not a solo queue")

        self.queue = queue

    def __call__(
        self,
        func=None,
        *,
        ignore_result=False,
        retry_on=(),
        delayed_retry=True,
        ignore_errors=(),
        singleton=False,
    ):
        """
        Decorator for Celery tasks that sets the queue and acks_late options

        Args
        ----
            func: The function to decorate

        Keyword Args
        ------------
            ignore_result: If the task should ignore the result
            retry_on: A tuple of exceptions that should trigger a retry on the delay queue
            delayed_retry: If the task should be retried after a delay
            ignore_errors: A tuple of exceptions that should be ignored when being run by celery
            singleton: If the task should be run as a singleton (only one concurrent execution at a time)
        """
        if func is None:
            # Called as @decorator(**extra_kwargs)
            return lambda func: self._decorator(
                func=func,
                ignore_result=ignore_result,
                retry_on=retry_on,
                delayed_retry=delayed_retry,
                ignore_errors=ignore_errors,
                singleton=singleton,
            )
        else:
            # Called as @decorator or @decorator(func)
            return self._decorator(
                func=func,
                ignore_result=ignore_result,
                retry_on=retry_on,
                delayed_retry=delayed_retry,
                ignore_errors=ignore_errors,
                singleton=singleton,
            )

    def _decorator(
        self,
        *,
        func,
        ignore_result,
        retry_on,
        delayed_retry,
        ignore_errors,
        singleton,
    ):
        @wraps(func)
        def wrapper(*args, _retries=0, **kwargs):
            is_in_celery_context = task_func.request.id is not None
            task_func._retry = lambda: _retry(
                task=task_func,
                signature_kwargs={
                    "args": args,
                    "kwargs": kwargs,
                    "immutable": True,
                },
                retries=_retries,
                delayed=delayed_retry,
            )

            try:
                if singleton:
                    with cache.lock(
                        _cache_key_from_method(func),
                        timeout=settings.CELERY_TASK_TIME_LIMIT,
                        blocking_timeout=5,
                    ):
                        return func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as error:
                if any(isinstance(error, e) for e in ignore_errors):
                    if is_in_celery_context:
                        logger.info(
                            f"Ignoring error in task {task_func.name}: {repr(error)}"
                        )
                        return
                    else:
                        raise error
                elif any(isinstance(error, e) for e in retry_on) or (
                    singleton and isinstance(error, LockError)
                ):
                    logger.info(
                        f"Retrying task {task_func.name} due to error: {error}, {_retries=}"
                    )
                    return task_func._retry()
                else:
                    raise error

        task_func = shared_task(
            acks_late=True,
            reject_on_worker_lost=True,
            queue=self.queue,
            ignore_result=ignore_result,
        )(wrapper)

        return task_func


# For idempotent tasks that take a long time (<7200s)
# or require a large amount of memory
acks_late_2xlarge_task = AcksLateTaskDecorator("acks-late-2xlarge")

# For idempotent tasks that take a short time (<300s)
# and do not require a large amount of memory
acks_late_micro_short_task = AcksLateTaskDecorator("acks-late-micro-short")
