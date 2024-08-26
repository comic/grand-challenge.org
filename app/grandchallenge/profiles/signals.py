from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from grandchallenge.profiles.models import BannedEmailAddress


@receiver(pre_delete, sender=get_user_model())
def ban_emails_of_deleted_users(instance, **__):
    BannedEmailAddress.objects.get_or_create(
        email=instance.email,
        defaults={
            "reason": f"Primary email address of deleted user {instance.username} (last login: {instance.last_login})"
        },
    )

    try:
        if instance.verification.email_is_verified:
            BannedEmailAddress.objects.get_or_create(
                email=instance.verification.email,
                defaults={
                    "reason": f"Verified verification email address of deleted user {instance.username}"
                },
            )
    except ObjectDoesNotExist:
        pass

    for address in EmailAddress.objects.filter(
        user=instance, verified=True, primary=False
    ):
        BannedEmailAddress.objects.get_or_create(
            email=address.email,
            defaults={
                "reason": f"Verified non-primary email address of deleted user {instance.username}"
            },
        )
