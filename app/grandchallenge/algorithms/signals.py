# -*- coding: utf-8 -*-
from django.db.models.signals import post_save
from django.dispatch import receiver
from nbconvert import HTMLExporter

from grandchallenge.algorithms.models import Job, Algorithm
from grandchallenge.algorithms.tasks import execute_algorithm


@receiver(post_save, sender=Job)
def execute_job(instance: Job = None, created: bool = False, *_, **__):
    if created:
        execute_algorithm.apply_async(
            task_id=str(instance.pk), kwargs={"job_pk": instance.pk}
        )

@receiver(post_save, sender=Algorithm)
def update_description_html(instance: Algorithm = None, *_, **__):
    # Run nbconvert on the description and get the html on each save
    html_exporter = HTMLExporter()
    html_exporter.template_file = 'full'

    with instance.description.open() as d:
       (body, _) = html_exporter.from_file(d)

    Algorithm.objects.filter(pk=instance.pk).update(description_html=body)
