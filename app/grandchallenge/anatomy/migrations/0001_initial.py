# Generated by Django 3.1.1 on 2020-12-02 13:08

import django.contrib.postgres.fields.citext
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BodyRegion",
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
                    "region",
                    django.contrib.postgres.fields.citext.CICharField(
                        max_length=16, unique=True
                    ),
                ),
            ],
            options={"ordering": ("region",)},
        ),
        migrations.CreateModel(
            name="BodyStructure",
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
                    "structure",
                    django.contrib.postgres.fields.citext.CICharField(
                        max_length=16, unique=True
                    ),
                ),
                (
                    "region",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="anatomy.bodyregion",
                    ),
                ),
            ],
            options={"ordering": ("region", "structure")},
        ),
    ]