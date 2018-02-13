# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import evaluation.validators
import evaluation.models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation', '0004_auto_20180212_1629'),
    ]

    operations = [
        migrations.AddField(
            model_name='config',
            name='show_supplementary_file_link',
            field=models.BooleanField(default=False, help_text='Show a link to download the supplementary file on the results page.'),
        ),
        migrations.AddField(
            model_name='config',
            name='supplementary_file_label',
            field=models.CharField(max_length=32, blank=True, default='Supplementary File', help_text='The label that will be used on the submission and results page for the supplementary file. For example: Algorithm Description.'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='supplementary_file',
            field=models.FileField(blank=True, validators=[evaluation.validators.MimeTypeValidator(allowed_types=('text/plain', 'application/pdf'))], upload_to=evaluation.models.submission_supplementary_file_path),
        ),
    ]
