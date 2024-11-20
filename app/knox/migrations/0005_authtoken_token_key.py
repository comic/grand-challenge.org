# Generated by Django 1.10 on 2016-08-18 09:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("knox", "0004_authtoken_expires"),
    ]

    operations = [
        migrations.AddField(
            model_name="authtoken",
            name="token_key",
            field=models.CharField(
                blank=True, db_index=True, max_length=8, null=True
            ),
        ),
    ]