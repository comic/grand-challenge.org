from django.db import migrations

from grandchallenge.profiles.models import NotificationSubscriptionOptions


def migrate_notification_email_preferences(apps, _schema_editor):
    UserProfile = apps.get_model("profiles", "UserProfile")  # noqa: N806
    UserProfile.objects.filter(receive_notification_emails=True).update(
        notification_email_choice=NotificationSubscriptionOptions.DAILY_SUMMARY
    )
    UserProfile.objects.filter(receive_notification_emails=False).update(
        notification_email_choice=NotificationSubscriptionOptions.DISABLED
    )


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0015_userprofile_notification_email_choice"),
    ]

    operations = [
        migrations.RunPython(migrate_notification_email_preferences),
    ]
