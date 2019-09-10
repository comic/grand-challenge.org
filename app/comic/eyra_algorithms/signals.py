from django.db.models.signals import post_delete
from django.dispatch import receiver
from comic.eyra_algorithms.models import Algorithm


@receiver(post_delete, sender=Algorithm)
def delete_algorithm_admin_group(
    sender, instance, *args, **kwargs
):
    if instance.admin_group:
        instance.admin_group.delete()
