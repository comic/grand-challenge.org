# Generated by Django 4.2.16 on 2024-10-02 11:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("evaluation", "0061_phase_submission_page_markdown"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="phase",
            name="submission_page_html",
        ),
    ]
