# Generated by Django 3.2.13 on 2022-05-05 09:52

from django.db import migrations

import grandchallenge.publications.fields


class Migration(migrations.Migration):

    dependencies = [
        ("publications", "0004_publication_citation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="publication",
            name="identifier",
            field=grandchallenge.publications.fields.IdentifierField(
                help_text="The DOI, e.g., 10.1002/mrm.25227, or the arXiv id, e.g., 2006.12449",
                unique=True,
            ),
        ),
    ]