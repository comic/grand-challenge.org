# Generated by Django 3.2.12 on 2022-03-18 08:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reader_studies", "0019_readerstudy_hanging_protocol"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="displayset",
            options={"ordering": ("order", "created")},
        ),
        migrations.AddField(
            model_name="displayset",
            name="order",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]