# Generated by Django 4.2.9 on 2024-01-26 14:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "organizations",
            "0005_organizationgroupobjectpermission_organizationuserobjectpermission",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="exempt_from_base_costs",
            field=models.BooleanField(
                default=False,
                help_text="If true, members of this organization will not be charged for base costs.",
            ),
        ),
    ]