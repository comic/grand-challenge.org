from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

from grandchallenge.verifications.models import Verification


def run():
    get_user_model().objects.filter(username="superuser").delete()
    su = get_user_model().objects.create_superuser(
        "superuser", "superuser@example.com", "superuser"
    )
    su.user_profile.receive_newsletter = False
    su.user_profile.save()
    EmailAddress.objects.filter(email=su.email).delete()
    EmailAddress.objects.create(
        user=su, email=su.email, verified=True, primary=True
    )
    Verification.objects.create(user=su, is_verified=True)
    print("Created superuser with username and password: superuser")
