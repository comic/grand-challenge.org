# Generated by Django 4.1.13 on 2023-11-29 09:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "profiles",
            "0013_userprofilegroupobjectpermission_userprofileuserobjectpermission",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="unread_messages_email_last_sent_at",
            field=models.DateTimeField(
                default=None, editable=False, null=True
            ),
        ),
    ]
