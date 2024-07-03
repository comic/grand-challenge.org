from django.db.models.signals import pre_delete
from django.dispatch import receiver

from grandchallenge.algorithms.models import AlgorithmImage, AlgorithmModel
from grandchallenge.evaluation.models import EvaluationGroundTruth, Method


@receiver(pre_delete, sender=AlgorithmImage)
@receiver(pre_delete, sender=AlgorithmModel)
@receiver(pre_delete, sender=EvaluationGroundTruth)
@receiver(pre_delete, sender=Method)
def delete_file_from_s3(instance, **_):
    instance._client.delete_object(Bucket=instance.bucket, Key=instance.key)
