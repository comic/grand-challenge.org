import base64

from allauth.mfa.adapter import get_adapter
from allauth.mfa.models import Authenticator
from django.db import migrations
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice


def migrate_mfa(apps, schema_editor):
    adapter = get_adapter()
    authenticators = []
    for totp in TOTPDevice.objects.filter(confirmed=True).iterator():
        recovery_codes = set()
        for sdevice in StaticDevice.objects.filter(
            confirmed=True, user_id=totp.user_id
        ).iterator():
            recovery_codes.update(
                sdevice.token_set.values_list("token", flat=True)
            )
        secret = base64.b32encode(bytes.fromhex(totp.key)).decode("ascii")
        totp_authenticator = Authenticator(
            user_id=totp.user_id,
            type=Authenticator.Type.TOTP,
            data={"secret": adapter.encrypt(secret)},
        )
        authenticators.append(totp_authenticator)
        authenticators.append(
            Authenticator(
                user_id=totp.user_id,
                type=Authenticator.Type.RECOVERY_CODES,
                data={
                    "migrated_codes": [
                        adapter.encrypt(c) for c in recovery_codes
                    ],
                },
            )
        )
        Authenticator.objects.bulk_create(authenticators)


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0018_remove_userprofile_receive_notification_emails"),
    ]

    operations = [
        migrations.RunPython(migrate_mfa, elidable=True),
    ]
