# Generated by Django 3.0.2 on 2020-01-30 20:37

import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ArchiveDataModel",
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
                    "value",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        encoder=django.core.serializers.json.DjangoJSONEncoder
                    ),
                ),
                ("modified", models.DateTimeField(auto_now=True)),
            ],
        )
    ]