# Generated by Django 3.1.1 on 2020-11-20 12:24

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Credit",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "credits",
                    models.PositiveIntegerField(
                        default=1000,
                        help_text="The credits that a user can spend per month on running algorithms.",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_credit",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        )
    ]