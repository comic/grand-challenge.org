# Generated by Django 4.2.14 on 2024-08-06 14:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("verifications", "0005_alter_verification_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="verificationuserset",
            name="auto_deactivate",
            field=models.BooleanField(
                default=False,
                help_text="Whether to automatically deactivate users added to this set",
            ),
        ),
        migrations.AddField(
            model_name="verificationuserset",
            name="comment",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="verificationuserset",
            name="is_false_positive",
            field=models.BooleanField(
                default=False, help_text="If this set was created in error"
            ),
        ),
    ]