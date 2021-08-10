from actstream.models import Follow
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from grandchallenge.evaluation.models import Phase


@receiver(pre_delete, sender=Phase)
def clean_up_submission_follows(instance, **_):
    ct = ContentType.objects.filter(
        app_label=instance._meta.app_label, model=instance._meta.model_name
    ).get()
    Follow.objects.filter(object_id=instance.pk, content_type=ct).delete()
