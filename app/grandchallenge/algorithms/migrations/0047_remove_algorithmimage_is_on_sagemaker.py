# Generated by Django 4.2.9 on 2024-01-24 09:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("algorithms", "0046_algorithmimage_desired_gpu_type"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="algorithmimage",
            name="is_on_sagemaker",
        ),
    ]