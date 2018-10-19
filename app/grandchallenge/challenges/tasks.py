from celery import shared_task

from grandchallenge.challenges.models import Challenge, ExternalChallenge


@shared_task
def update_filter_classes():
    lookup = ("task_types", "modalities", "structures__region", "creator")

    for obj in [Challenge, ExternalChallenge]:
        for c in obj.objects.prefetch_related(*lookup).all():
            classes = c.get_filter_classes()
            obj.objects.filter(pk=c.pk).update(filter_classes=classes)
