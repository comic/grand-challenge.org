from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django_otp.plugins.otp_static.models import StaticToken

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

    su.totpdevice_set.create()
    static_device = su.staticdevice_set.create(name="backup")

    for _ in range(5):
        token = StaticToken.random_token()
        static_device.token_set.create(token=token)
        print(f"Added one time token: {token}")
