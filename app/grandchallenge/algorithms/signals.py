# -*- coding: utf-8 -*-
from django.db.models.signals import post_save
from django.dispatch import receiver

from grandchallenge.algorithms.models import Job
from grandchallenge.algorithms.tasks import execute_algorithm


@receiver(post_save, sender=Job)
def execute_job(instance: Job = None, created: bool = False, *_, **__):
    if created:
        execute_algorithm.apply_async(
            task_id=str(instance.pk), kwargs={"job_pk": instance.pk}
        )
