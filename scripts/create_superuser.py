from allauth.account.models import EmailAddress
from allauth.mfa import recovery_codes, totp
from django.contrib.auth import get_user_model

from grandchallenge.verifications.models import Verification


def run():
    username = "superuser"

    get_user_model().objects.filter(username=username).delete()

    su = get_user_model().objects.create_superuser(
        username=username, email=f"{username}@example.com", password=username
    )
    print(f"Created superuser with username and password: {username}")

    su.user_profile.receive_newsletter = False
    su.user_profile.save()

    EmailAddress.objects.filter(email=su.email).delete()
    EmailAddress.objects.create(
        user=su, email=su.email, verified=True, primary=True
    )
    Verification.objects.create(user=su, email=su.email, is_verified=True)

    totp.TOTP.activate(su, totp.generate_totp_secret())
    recovery_code_device = recovery_codes.RecoveryCodes.activate(su)
    codes = recovery_code_device.generate_codes()

    for token in codes:
        print(f"Added one time token: {token}")
