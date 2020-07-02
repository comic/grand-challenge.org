from typing import Union

from django.db.models.signals import post_save
from django.dispatch import receiver

from grandchallenge.core.utils import disable_for_loaddata
from grandchallenge.evaluation.models import (
    Config,
    Result,
)
from grandchallenge.evaluation.tasks import calculate_ranks


@receiver(post_save, sender=Config)
@receiver(post_save, sender=Result)
@disable_for_loaddata
def recalculate_ranks(instance: Union[Result, Config] = None, *_, **__):
    """Recalculates the ranking on a new result"""
    calculate_ranks.apply_async(kwargs={"challenge_pk": instance.challenge.pk})
