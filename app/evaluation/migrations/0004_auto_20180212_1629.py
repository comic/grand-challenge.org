# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import evaluation.models
import evaluation.validators


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation', '0003_auto_20180212_1205'),
    ]

    operations = [
        migrations.AddField(
            model_name='config',
            name='require_supplementary_file',
            field=models.BooleanField(default=False, help_text='Force users to include a supplementary file with their predictions file (eg, include a pdf description of the method).'),
        ),
        migrations.AddField(
            model_name='config',
            name='supplementary_file_help_text',
            field=models.CharField(max_length=128, blank=True, default='', help_text='The help text to include on the submissions page to describe the submissions file. Eg: "A PDF description of the method.".'),
        ),
        migrations.AddField(
            model_name='submission',
            name='supplementary_file',
            field=models.FileField(blank=True, validators=[evaluation.validators.MimeTypeValidator(allowed_types=('text/plain', 'application/pdf'))], upload_to=evaluation.models.submission_file_path),
        ),
    ]
