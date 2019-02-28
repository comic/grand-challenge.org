from django.dispatch import receiver
from django.db.models.signals import post_save
from guardian.shortcuts import assign_perm
from django.conf import settings

from grandchallenge.annotations.models import (
    MeasurementAnnotation,
    BooleanClassificationAnnotation,
    IntegerClassificationAnnotation,
    PolygonAnnotationSet,
    LandmarkAnnotationSet,
    ETDRSGridAnnotation,
    CoordinateListAnnotation,
    SinglePolygonAnnotation,
    SingleLandmarkAnnotation,
)
from config.settings import PERMISSION_TYPES


@receiver(post_save, sender=MeasurementAnnotation)
@receiver(post_save, sender=BooleanClassificationAnnotation)
@receiver(post_save, sender=IntegerClassificationAnnotation)
@receiver(post_save, sender=PolygonAnnotationSet)
@receiver(post_save, sender=LandmarkAnnotationSet)
@receiver(post_save, sender=ETDRSGridAnnotation)
@receiver(post_save, sender=CoordinateListAnnotation)
@receiver(post_save, sender=SinglePolygonAnnotation)
@receiver(post_save, sender=SingleLandmarkAnnotation)
def annotation_post_save(sender, instance, created):
    """
    Set object level permissions for grader that belongs to retina_graders group after saving
    of new annotation
    """
    if not created:
        return

    model_name = sender.__name__.lower()
    if model_name.startswith("single"):
        owner = instance.annotation_set.grader
    else:
        owner = instance.grader

    if not owner.groups.filter(
        name=settings.RETINA_GRADERS_GROUP_NAME
    ).exists():
        return

    for permission_type in PERMISSION_TYPES:
        permission_name = f"annotation.{permission_type}_{model_name}"
        assign_perm(permission_name, owner, instance)
