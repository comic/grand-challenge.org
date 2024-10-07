# Generated by Django 4.2.15 on 2024-09-18 07:40
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import migrations


def set_is_active_until(apps, schema_editor):
    Challenge = apps.get_model("challenges", "challenge")  # noqa: N806

    for challenge in Challenge.objects.all():
        challenge.is_active_until = challenge.created.date() + relativedelta(
            months=settings.CHALLENGES_DEFAULT_ACTIVE_MONTHS
        )
        challenge.save()


class Migration(migrations.Migration):

    dependencies = [
        ("challenges", "0040_challenge_is_active_until"),
    ]

    operations = [migrations.RunPython(set_is_active_until, elidable=True)]