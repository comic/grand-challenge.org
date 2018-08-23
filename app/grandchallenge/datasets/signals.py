# -*- coding: utf-8 -*-
import logging
from typing import Union

from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from grandchallenge.cases.models import Image
from grandchallenge.datasets.models import AnnotationSet

logger = logging.getLogger(__name__)


@receiver(m2m_changed, sender=AnnotationSet.images.through)
def update_annotations(
    sender: AnnotationSet.images.through,
    instance: Union[AnnotationSet, Image] = None,
    action: str = None,
    reverse: bool = False,
    pk_set: set = None,
    **__,
):
    """ Update the annotation set after the list of images has changed """
    logger.debug(f"Signal hit. Sender {sender}. Action {action}.")
    # Note: Do not use disable_for_loaddata as the "raw" key is not sent
    # See documentation about args sent to this function:
    # https://docs.djangoproject.com/en/2.1/ref/signals/#m2m-changed
    if isinstance(sender, AnnotationSet.images.through) and "post" in action:
        if not reverse:
            # Forward relation, so instance is the AnnotationSet
            instance.match_images()
        else:
            # Reverse relation, so need to get the AnnotationSets
            for pk in pk_set:
                annotationset = AnnotationSet.objects.get(pk=pk)
                annotationset.match_images()
