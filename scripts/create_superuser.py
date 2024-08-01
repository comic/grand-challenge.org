from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model

from grandchallenge.verifications.models import Verification
from tests.factories import activate_2fa


def run():
    username = "superuser"

    get_user_model().objects.filter(username=username).delete()

    su = get_user_model().objects.create_superuser(
        username=username, email=f"{username}@example.com", password=username
    )
    print(f"Created superuser with username and password: {username}")

    su.user_profile.receive_newsletter = False
    su.user_profile.save()

    EmailAddress.objects.create(
        user=su, email=su.email, verified=True, primary=True
    )

    Verification.objects.create(user=su, email=su.email, is_verified=True)

    activate_2fa(user=su)

    device = Authenticator.objects.get(
        user=su, type=Authenticator.Type.RECOVERY_CODES
    )

    for token in device.wrap().get_unused_codes():
        print(f"Added one time token: {token}")
